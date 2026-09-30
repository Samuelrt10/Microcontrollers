from machine import Pin, I2C
import time
from machine_i2c_lcd import I2cLcd # Librería externa necesaria para la LCD

# ==========================================
# 1. CONFIGURACIÓN DE LA PANTALLA LCD I2C
# ==========================================
# Pines I2C por defecto en ESP32 suelen ser SCL=22, SDA=21
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
direccion_i2c = 0x27 # Cambiar a 0x3F si la pantalla no responde

# Iniciar LCD (I2C, Dirección, Filas, Columnas)
lcd = I2cLcd(i2c, direccion_i2c, 2, 16)

# ==========================================
# 2. CONFIGURACIÓN DEL TECLADO 4x4
# ==========================================
matriz_teclas = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]

# Definir los pines conectados a filas y columnas
pines_filas = [19, 18, 5, 17]
pines_columnas = [16, 4, 2, 15]

# Las filas son salidas, inicialmente en ALTO (1)
filas = [Pin(pin, Pin.OUT, value=1) for pin in pines_filas]
# Las columnas son entradas con resistencia PULL_UP interna
columnas = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in pines_columnas]

def leer_teclado():
    tecla_presionada = None
    for i, fila in enumerate(filas):
        # Poner la fila actual en BAJO (0) para escanearla
        fila.value(0)
        
        for j, columna in enumerate(columnas):
            # Si el botón está presionado, la columna lee un BAJO (0)
            if columna.value() == 0:
                tecla_presionada = matriz_teclas[i][j]
                
                # Esperar a que se suelte el botón para evitar múltiples lecturas
                while columna.value() == 0:
                    time.sleep(0.01)
                    
        # Devolver la fila a su estado ALTO (1)
        fila.value(1)
        
        if tecla_presionada:
            break
            
    return tecla_presionada

# ==========================================
# 3. BUCLE PRINCIPAL
# ==========================================
lcd.clear()
lcd.putstr("Esperando dato..")

while True:
    tecla = leer_teclado()
    
    if tecla:
        # 1. Actualizar la LCD
        lcd.clear()
        lcd.putstr("Enviando trazo:\n")
        lcd.putstr(f"       {tecla}")
        
        # 2. Enviar por puerto serial (USB) a la computadora
        print(tecla)
        
        # Pequeño retardo antirrebote adicional
        time.sleep(0.1)