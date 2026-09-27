import machine
import time
import sys
import select

# Configuración de pines para los LEDs usando PWM
# Ajusta los números de pines según cómo hayas cableado tu ESP32
led_amarillo = machine.PWM(machine.Pin(12), freq=1000)
led_azul = machine.PWM(machine.Pin(14), freq=1000)
led_rojo = machine.PWM(machine.Pin(27), freq=1000)

# Aseguramos que inician apagados
led_amarillo.duty(0)
led_azul.duty(0)
led_rojo.duty(0)

# Configurar el sistema de lectura no bloqueante desde el puerto serie (USB)
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)


def apagar_todos():
    led_amarillo.duty(0)
    led_azul.duty(0)
    led_rojo.duty(0)


def secuencia_modo_1():
    print("Ejecutando Modo 1 (Secuencia pulgar abajo)")
    # Ejemplo de secuencia: Parpadeo alterno
    for _ in range(3):
        apagar_todos()
        led_rojo.duty(1023)
        time.sleep(0.2)
        apagar_todos()
        led_azul.duty(1023)
        time.sleep(0.2)
    apagar_todos()


def secuencia_modo_2():
    print("Ejecutando Modo 2 (Secuencia pulgar arriba)")
    # Ejemplo de secuencia: Todos parpadean al mismo tiempo
    for _ in range(4):
        led_amarillo.duty(1023)
        led_azul.duty(1023)
        led_rojo.duty(1023)
        time.sleep(0.3)
        apagar_todos()
        time.sleep(0.3)


# Bucle principal
print("ESP32 lista para recibir comandos.")
while True:
    # Revisar si hay datos en el puerto serie (timeout de 10ms)
    res = poller.poll(10)
    if res:
        comando = sys.stdin.read(1)

        # Evaluar el comando recibido
        if comando == 'F':  # Closed Fist -> 30% Amarillo
            apagar_todos()
            led_amarillo.duty(int(1023 * 0.30))
            print("Intensidad Amarilla: 30%")

        elif comando == 'V':  # Victory -> 70% Azul
            apagar_todos()
            led_azul.duty(int(1023 * 0.70))
            print("Intensidad Azul: 70%")

        elif comando == 'P':  # Open Palm -> 100% Rojo
            apagar_todos()
            led_rojo.duty(1023)  # 1023 es el 100% en MicroPython ESP32
            print("Intensidad Roja: 100%")

        elif comando == 'D':  # Thumb Down -> Primera Interrupción (Modo 1)
            secuencia_modo_1()

        elif comando == 'U':  # Thumb Up -> Segunda Interrupción (Modo 2)
            secuencia_modo_2()