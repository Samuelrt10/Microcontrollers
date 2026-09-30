import cv2
import numpy as np
import serial
from tensorflow.keras.models import load_model

# Configuración del puerto serie (ajusta el COM/ttyUSB según tu ESP32 Maestro)
puerto = serial.Serial('COM10', 9600, timeout=1)

# Cargar el modelo CNN previamente entrenado
modelo = load_model('mnist_model.h5')

cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

while True:
    ret, frame = cam.read()
    if not ret: break

    # Dibujar un cuadro guía en el centro de la pantalla
    cv2.rectangle(frame, (200, 150), (400, 350), (0, 255, 0), 2)

    # Extraer la región de interés (ROI)
    roi = frame[150:350, 200:400]

    # Preprocesamiento OpenCV
    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, umbral = cv2.threshold(gris, 100, 255, cv2.THRESH_BINARY_INV)
    redimensionado = cv2.resize(umbral, (28, 28))
    normalizado = redimensionado / 255.0
    imagen_cnn = np.reshape(normalizado, (1, 28, 28, 1))

    # Reconocimiento CNN
    prediccion = modelo.predict(imagen_cnn, verbose=0)
    digito = np.argmax(prediccion)
    confianza = np.max(prediccion)

    # Si la confianza es alta, enviar el dato por puerto serie
    if confianza > 0.8:
        cv2.putText(frame, f"Numero: {digito} ({confianza * 100:.1f}%)", (200, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        puerto.write(str(digito).encode())

    cv2.imshow("Reconocimiento", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
puerto.close()