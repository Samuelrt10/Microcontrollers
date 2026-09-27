import os
import time
import cv2
import mediapipe as mp
import serial
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Configurar la comunicación serie con la ESP32
# ¡CUIDADO! Reemplaza 'COM3' por el puerto correcto de tu ESP32 (ej. '/dev/ttyUSB0' en Linux/Mac)
PUERTO_SERIE = 'COM5'
BAUD_RATE = 115200

try:
    esp32 = serial.Serial(PUERTO_SERIE, BAUD_RATE, timeout=0.1)
    print("Conexión serial establecida.")
except Exception as e:
    print(f"Error al conectar con el puerto serie: {e}")
    esp32 = None

# 2. Configurar el modelo de MediaPipe
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gesture_recognizer.task')
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.GestureRecognizerOptions(base_options=base_options)
recognizer = vision.GestureRecognizer.create_from_options(options)

# 3. Iniciar la cámara web
cap = cv2.VideoCapture(0)

# Variables para no saturar el envío por serial
ultimo_comando = ''
tiempo_ultimo_envio = 0

print("Presiona la tecla 'ESC' para salir.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Voltear la imagen en espejo para mayor comodidad y convertir a RGB
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # Reconocer los gestos en la imagen
    recognition_result = recognizer.recognize(mp_image)

    comando_actual = ''
    gesture_name = 'Ninguno'

    if recognition_result.gestures:
        # Obtener el gesto con mayor probabilidad
        top_gesture = recognition_result.gestures[0][0]
        gesture_name = top_gesture.category_name

        # Mapear los gestos a comandos para la ESP32
        if gesture_name == 'Closed_Fist':  # Puño
            comando_actual = 'F'
        elif gesture_name == 'Victory':  # Señal de Paz/V
            comando_actual = 'V'
        elif gesture_name == 'Open_Palm':  # Palma abierta
            comando_actual = 'P'
        elif gesture_name == 'Thumb_Down':  # Pulgar abajo
            comando_actual = 'D'
        elif gesture_name == 'Thumb_Up':  # Pulgar arriba
            comando_actual = 'U'

        # Enviar el comando por puerto serie (evitando envíos repetidos muy rápidos)
        tiempo_actual = time.time()
        if comando_actual != '' and esp32 is not None:
            if comando_actual != ultimo_comando or (tiempo_actual - tiempo_ultimo_envio) > 1.0:
                esp32.write(comando_actual.encode())
                ultimo_comando = comando_actual
                tiempo_ultimo_envio = tiempo_actual
                print(f"Gesto: {gesture_name} -> Enviando comando: {comando_actual}")

    # Mostrar en pantalla el gesto reconocido
    cv2.putText(frame, f'Gesto: {gesture_name}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow('Control de Gestos - Universidad Militar', frame)

    if cv2.waitKey(1) & 0xFF == 27:  # 27 es la tecla ESC
        break

cap.release()
cv2.destroyAllWindows()
if esp32:
    esp32.close()
