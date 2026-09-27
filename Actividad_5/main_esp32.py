"""
Actividad 5: Teleoperación de Brazo Robótico en PyBullet mediante Joystick y ESP32
Universidad Militar Nueva Granada - Microcontroladores
Autor: Samuel Rubio Tamberg

Firmware MicroPython para ESP32:
- Lectura de dos ejes analógicos del Joystick (VRx en GPIO 34, VRy en GPIO 35).
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
CENTRO_ADC = 2048
ZONA_MUERTA = 250     # Rango central considerado reposo para evitar drift
MAX_ADC = 4095

modo_actual = 0       # 0: Base/Hombro, 1: Codo/Pinza
ultimo_estado_sw = 1
tiempo_ultimo_debounce = 0
DEBOUNCE_MS = 250


def normalizar_eje(valor_crudo):
    """
    Convierte la lectura ADC (0-4095) a un rango normalizado (-1.0 a 1.0)
    aplicando filtro de zona muerta alrededor del centro.
    """
    desviacion = valor_crudo - CENTRO_ADC
    if abs(desviacion) < ZONA_MUERTA:
        return 0.0

    if desviacion > 0:
        norm = (desviacion - ZONA_MUERTA) / (MAX_ADC - CENTRO_ADC - ZONA_MUERTA)
        return min(max(norm, 0.0), 1.0)
    else:
        norm = (desviacion + ZONA_MUERTA) / (CENTRO_ADC - ZONA_MUERTA)
        return min(max(norm, -1.0), 0.0)


# ==============================================================================
# 3. BUCLE PRINCIPAL DE MUESTREO Y TRANSMISIÓN UART
# ==============================================================================
print("ESP32 Joystick teleoperation iniciada. Enviando telemetria...")

while True:
    t_inicio = time.ticks_ms()

    # Lectura de los potenciómetros del joystick
    raw_x = adc_x.read()
    raw_y = adc_y.read()

    norm_x = normalizar_eje(raw_x)
    norm_y = normalizar_eje(raw_y)

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
    # Ejemplo: "0.45,-0.80,0,0\n"
    trama = f"{norm_x:.2f},{norm_y:.2f},{sw_presionado},{modo_actual}\n"
    sys.stdout.write(trama)

    # Mantener tasa de transmisión uniforme a ~50 Hz (20 ms por ciclo)
    t_transcurrido = time.ticks_diff(time.ticks_ms(), t_inicio)
    t_espera = 20 - t_transcurrido
    if t_espera > 0:
        time.sleep_ms(t_espera)
