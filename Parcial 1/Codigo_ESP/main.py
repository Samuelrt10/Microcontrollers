import sys
import uselect
import time
from machine import Pin, PWM, ADC, SoftI2C

# ==========================================================
# 1. FUNCIÓN DE DESBLOQUEO I2C
# ==========================================================
def recuperar_bus_i2c(pin_sda, pin_scl):
    scl = Pin(pin_scl, Pin.OUT)
    sda = Pin(pin_sda, Pin.IN, Pin.PULL_UP)

    scl.value(1)
    time.sleep_ms(1)

    for _ in range(9):
        scl.value(0)
        time.sleep_us(10)
        scl.value(1)
        time.sleep_us(10)

    sda = Pin(pin_sda, Pin.OUT)
    sda.value(0)
    time.sleep_us(10)
    scl.value(1)
    time.sleep_us(10)
    sda.value(1)
    time.sleep_ms(5)

# ==========================================================
# 2. DRIVER DIRECTO LCD 1602 I2C
# ==========================================================
class LCD1602_I2C:
    def __init__(self, i2c, addr=0x27):
        self.i2c = i2c
        self.addr = addr
        self.backlight = 0x08

        time.sleep_ms(100)
        self._write_byte(0x33, 0)
        time.sleep_ms(10)
        self._write_byte(0x32, 0)
        time.sleep_ms(5)
        self._write_byte(0x28, 0)
        self._write_byte(0x0C, 0)
        self._write_byte(0x06, 0)
        self.clear()

    def _write_nibble(self, nibble, mode):
        data = (nibble & 0xF0) | mode | self.backlight
        self.i2c.writeto(self.addr, bytearray([data | 0x04]))
        time.sleep_us(500)
        self.i2c.writeto(self.addr, bytearray([data & ~0x04]))
        time.sleep_us(500)

    def _write_byte(self, byte, mode):
        self._write_nibble(byte & 0xF0, mode)
        self._write_nibble((byte << 4) & 0xF0, mode)

    def clear(self):
        self._write_byte(0x01, 0)
        time.sleep_ms(3)

    def set_cursor(self, col, row):
        addr = col + (0x40 if row > 0 else 0x00)
        self._write_byte(0x80 | addr, 0)

    def print_str(self, text, col=0, row=0):
        try:
            self.set_cursor(col, row)
            for char in text[:16]:
                self._write_byte(ord(char), 1)
        except Exception:
            pass

# ==========================================================
# 3. CONFIGURACIÓN DE PINES
# ==========================================================

# LCD I2C
PIN_SDA = 25
PIN_SCL = 26

# Panel solar
PIN_ADC_SOLAR = 34

# Voltaje producido por el motor DC
# Cambia este pin si lo necesitas.
PIN_ADC_MOTOR = 35

# Sensores Hall digitales, separados físicamente 90°
# Cambia los GPIO si tu montaje usa otros pines.
PIN_HALL_A = 32
PIN_HALL_B = 33

# LEDs PWM
PIN_LED1 = 22
PIN_LED2 = 23

# ==========================================================
# 4. INICIALIZACIÓN DE HARDWARE
# ==========================================================
recuperar_bus_i2c(PIN_SDA, PIN_SCL)

adc_solar = ADC(Pin(PIN_ADC_SOLAR))
adc_solar.atten(ADC.ATTN_11DB)

adc_motor = ADC(Pin(PIN_ADC_MOTOR))
adc_motor.atten(ADC.ATTN_11DB)

led1 = PWM(Pin(PIN_LED1), freq=1000, duty_u16=0)
led2 = PWM(Pin(PIN_LED2), freq=1000, duty_u16=0)

# Sensores Hall digitales.
# Se usa pull-up interno, adecuado para sensores con salida open-collector.
hall_a = Pin(PIN_HALL_A, Pin.IN, Pin.PULL_UP)
hall_b = Pin(PIN_HALL_B, Pin.IN, Pin.PULL_UP)

# ==========================================================
# 5. VARIABLES PARA RPM Y SENTIDO DE GIRO
# ==========================================================

# Si tienes un imán o una marca por vuelta: 1.
# Si tienes N imanes/marcas por revolución, cambia este valor a N.
PULSOS_POR_REV = 1

# Protección contra rebotes/ruido de sensores Hall, en microsegundos.
TIEMPO_ANTI_REBOTE_US = 1500

ultimo_pulso_us = 0
periodo_pulso_us = 0
ultimo_evento_hall_us = 0

rpm_motor = 0.0
direccion_motor = 1
contador_pulsos = 0

# ==========================================================
# 6. INTERRUPCIONES DE SENSORES HALL
# ==========================================================

def irq_hall_a(pin):
    global ultimo_pulso_us
    global periodo_pulso_us
    global ultimo_evento_hall_us
    global contador_pulsos
    global direccion_motor

    ahora_us = time.ticks_us()

    # Antirrebote para evitar falsos pulsos.
    if time.ticks_diff(ahora_us, ultimo_evento_hall_us) < TIEMPO_ANTI_REBOTE_US:
        return

    ultimo_evento_hall_us = ahora_us

    # La lectura del Hall B indica el sentido de giro.
    # Si el sentido aparece invertido, intercambia 1 y -1.
    if hall_b.value() == 1:
        direccion_motor = 1
    else:
        direccion_motor = -1

    if ultimo_pulso_us != 0:
        periodo = time.ticks_diff(ahora_us, ultimo_pulso_us)

        if periodo > 0:
            periodo_pulso_us = periodo

    ultimo_pulso_us = ahora_us
    contador_pulsos += 1

def irq_hall_b(pin):
    global direccion_motor

    # Hall B se conserva para detectar cuadratura/sentido.
    # Hall A es la referencia de tiempo para obtener RPM.
    if hall_a.value() == 0:
        direccion_motor = 1
    else:
        direccion_motor = -1

# Se emplean flancos ascendentes; MicroPython permite asociar
# manejadores de interrupción con Pin.irq(). [1][3]
hall_a.irq(trigger=Pin.IRQ_RISING, handler=irq_hall_a)
hall_b.irq(trigger=Pin.IRQ_RISING, handler=irq_hall_b)

# ==========================================================
# 7. CALIBRACIÓN LED
# ==========================================================
DUTY_APAGADO = 0
DUTY_MEDIO = 12000
DUTY_ALTO = 65535

nivel_actual = 0

# ==========================================================
# 8. LCD
# ==========================================================
lcd = None

try:
    i2c = SoftI2C(
        sda=Pin(PIN_SDA),
        scl=Pin(PIN_SCL),
        freq=100000
    )

    dispositivos = i2c.scan()
    dir_lcd = dispositivos[0] if dispositivos else 0x27

    lcd = LCD1602_I2C(i2c, addr=dir_lcd)
    lcd.print_str("ASADOR SOLAR IA", 0, 0)
    lcd.print_str("Sistema listo", 0, 1)
    time.sleep_ms(1000)
    lcd.clear()

except Exception as e:
    print("Aviso LCD:", e)

# ==========================================================
# 9. FUNCIONES DE MEDICIÓN
# ==========================================================

def actualizar_leds(nivel):
    pwm1 = DUTY_APAGADO
    pwm2 = DUTY_APAGADO

    if nivel == 1:
        pwm1 = DUTY_MEDIO
        pwm2 = DUTY_APAGADO

    elif nivel == 2:
        pwm1 = DUTY_MEDIO
        pwm2 = DUTY_MEDIO

    elif nivel == 3:
        pwm1 = DUTY_ALTO
        pwm2 = DUTY_MEDIO

    elif nivel == 4:
        pwm1 = DUTY_ALTO
        pwm2 = DUTY_ALTO

    led1.duty_u16(pwm1)
    led2.duty_u16(pwm2)

def leer_voltaje(adc, muestras=10):
    suma_uv = 0

    for _ in range(muestras):
        suma_uv += adc.read_uv()

    return (suma_uv / muestras) / 1_000_000.0

def leer_potencia_panel_mw():
    voltaje = leer_voltaje(adc_solar)

    if voltaje < 0.05:
        return 0.0

    # Modelo que ya tenías: corriente proporcional hasta 200 mA.
    corriente_ma = min(200.0, (voltaje / 2.5) * 200.0)

    # V × mA = mW
    return voltaje * corriente_ma

def leer_potencia_motor_mw():
    voltaje = leer_voltaje(adc_motor)

    if voltaje < 0.05:
        return 0.0

    # Corriente asumida: 250 mA = 0.25 A.
    # V × mA = mW
    corriente_ma = 250.0

    return voltaje * corriente_ma

def calcular_rpm():
    global rpm_motor

    periodo = periodo_pulso_us
    ultimo = ultimo_pulso_us

    if periodo <= 0 or ultimo == 0:
        rpm_motor = 0.0
        return rpm_motor

    tiempo_desde_ultimo = time.ticks_diff(time.ticks_us(), ultimo)

    # Si no hay pulsos durante dos segundos, se considera detenido.
    if tiempo_desde_ultimo > 2_000_000:
        rpm_motor = 0.0
        return rpm_motor

    # RPM = 60,000,000 / (periodo_us × pulsos_por_revolución)
    rpm_motor = 60_000_000.0 / (periodo * PULSOS_POR_REV)

    return rpm_motor

# ==========================================================
# 10. SERIAL Y BUCLE PRINCIPAL
# ==========================================================
buffer_serial = ""
poll_stdin = uselect.poll()
poll_stdin.register(sys.stdin, uselect.POLLIN)

tiempo_previo_lcd = time.ticks_ms()

actualizar_leds(0)

while True:

    # Comandos seriales de 0 a 4: mantiene la lógica LED.
    if poll_stdin.poll(0):
        c = sys.stdin.read(1)

        if c in ("\n", "\r"):
            cmd = buffer_serial.strip()
            buffer_serial = ""

            if cmd.isdigit():
                val = int(cmd)

                if 0 <= val <= 4:
                    nivel_actual = val
                    actualizar_leds(nivel_actual)

        else:
            buffer_serial += c

    # Refresco LCD cada 250 ms.
    t_act = time.ticks_ms()

    if time.ticks_diff(t_act, tiempo_previo_lcd) >= 250:
        rpm = calcular_rpm()
        potencia_panel_mw = leer_potencia_panel_mw()
        potencia_motor_mw = leer_potencia_motor_mw()

        if lcd:
            # Línea 1: RPM
            lcd.print_str("RPM={:7.1f}   ".format(rpm), 0, 0)

            # Línea 2: F = potencia fotovoltaica; A = potencia del alternador
            # Formato limitado a 16 caracteres para LCD 1602.
            lcd.print_str(
                "F={:5.0f} A={:5.0f}".format(
                    potencia_panel_mw,
                    potencia_motor_mw
                ),
                0,
                1
            )

        tiempo_previo_lcd = t_act

    time.sleep_ms(10)