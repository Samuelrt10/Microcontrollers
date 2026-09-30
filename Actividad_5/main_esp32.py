"""
Actividad 5: Teleoperación de Brazo Robótico en PyBullet mediante Joystick y ESP32
Universidad Militar Nueva Granada - Microcontroladores
Autor: Samuel Rubio Tamberg

Firmware MicroPython para ESP32:
- Lectura de dos ejes analógicos del Joystick (VRx en GPIO 34, VRy en GPIO 35).
- Calibración automática del centro analógico en reposo al arrancar.
- Lectura de pulsador digital del Joystick (SW en GPIO 32 con PULL_UP).
- Tratamiento de señal: Zona muerta (deadband) y normalización (-1.0 a 1.0).
- Detección de flanco del botón SW para alternancia de modo conmutable:
    * Modo 0: Control de Articulación 1 (Base) y Articulación 2 (Hombro).
    * Modo 1: Control de Articulación 3 (Codo) y Pinza (Apertura / Cierre).
- Transmisión UART periódica (50 Hz / 20 ms) en formato estructurado: X,Y,SW_STATE,MODO
"""

import machine
import time
import sys

# ==============================================================================
# 1. CONFIGURACIÓN DE PINES
# ==============================================================================
PIN_VRX = 34   # Canal analógico ADC1_CH6
PIN_VRY = 35   # Canal analógico ADC1_CH7
PIN_SW  = 32   # Pulsador con pull-up interno

# Configuración de los ADCs (12 bits: 0 a 4095, atenuación 11 dB -> 0 a 3.3V)
adc_x = machine.ADC(machine.Pin(PIN_VRX))
adc_y = machine.ADC(machine.Pin(PIN_VRY))
adc_x.atten(machine.ADC.ATTN_11DB)
adc_y.atten(machine.ADC.ATTN_11DB)

# Configuración del pulsador (activo en bajo por PULL_UP)
btn_sw = machine.Pin(PIN_SW, machine.Pin.IN, machine.Pin.PULL_UP)

# ==============================================================================
# 2. PARÁMETROS DE CALIBRACIÓN Y TRATAMIENTO DE SEÑAL
# ==============================================================================
ZONA_MUERTA = 300     # Rango central considerado reposo para evitar drift
MAX_ADC = 4095

# Calibración dinámica del centro en reposo (promedio de 30 muestras al arrancar)
time.sleep_ms(200)
suma_x = 0
suma_y = 0
for _ in range(30):
    suma_x += adc_x.read()
    suma_y += adc_y.read()
    time.sleep_ms(10)

centro_adc_x = int(suma_x / 30)
centro_adc_y = int(suma_y / 30)

modo_actual = 0       # 0: Base/Hombro, 1: Codo/Pinza
ultimo_estado_sw = 1
tiempo_ultimo_debounce = 0
DEBOUNCE_MS = 250


def normalizar_eje(valor_crudo, centro_adc):
    """
    Convierte la lectura ADC (0-4095) a un rango normalizado (-1.0 a 1.0)
    aplicando el centro calibrado y filtro de zona muerta alrededor del centro.
    """
    desviacion = valor_crudo - centro_adc
    if abs(desviacion) < ZONA_MUERTA:
        return 0.0

    if desviacion > 0:
        denominador = max(1, MAX_ADC - centro_adc - ZONA_MUERTA)
        norm = (desviacion - ZONA_MUERTA) / denominador
        return min(max(norm, 0.0), 1.0)
    else:
        denominador = max(1, centro_adc - ZONA_MUERTA)
        norm = (desviacion + ZONA_MUERTA) / denominador
        return min(max(norm, -1.0), 0.0)


# ==============================================================================
# 3. BUCLE PRINCIPAL DE MUESTREO Y TRANSMISIÓN UART
# ==============================================================================
while True:
    t_inicio = time.ticks_ms()

    # Lectura de los potenciómetros del joystick con centro calibrado
    raw_x = adc_x.read()
    raw_y = adc_y.read()

    norm_x = normalizar_eje(raw_x, centro_adc_x)
    norm_y = normalizar_eje(raw_y, centro_adc_y)

    # Lectura y detección de flanco de bajada del botón (presionado = 0)
    estado_sw = btn_sw.value()
    t_actual = time.ticks_ms()

    sw_presionado = 0
    if estado_sw == 0 and ultimo_estado_sw == 1:
        if time.ticks_diff(t_actual, tiempo_ultimo_debounce) > DEBOUNCE_MS:
            # Alternar modo conmutable
            modo_actual = 1 if modo_actual == 0 else 0
            sw_presionado = 1
            tiempo_ultimo_debounce = t_actual

    ultimo_estado_sw = estado_sw

    # Formateo de la trama de transmisión serial (X,Y,SW_TRIGGER,MODO)
    trama = f"{norm_x:.2f},{norm_y:.2f},{sw_presionado},{modo_actual}\n"
    sys.stdout.write(trama)

    # Mantener tasa de transmisión uniforme a ~50 Hz (20 ms por ciclo)
    t_transcurrido = time.ticks_diff(time.ticks_ms(), t_inicio)
    t_espera = 20 - t_transcurrido
    if t_espera > 0:
        time.sleep_ms(t_espera)



