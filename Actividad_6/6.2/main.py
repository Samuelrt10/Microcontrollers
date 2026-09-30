import cv2
import numpy as np
import serial
from tensorflow.keras.models import load_model

# 1. Configuración de hardware y modelo
# Cambia 'COM3' por el puerto donde está conectado el ESP32 Maestro
try:
    puerto = serial.Serial('COM10', 9600, timeout=1)
except Exception as e:
    print(f"Error al abrir puerto serial: {e}")
    puerto = None

print("Cargando modelo neuronal...")
modelo = load_model('mnist_model.h5')

# Inicializar cámara con el backend DirectShow (Soluciona la pantalla negra/errores MSMF)
# Si el índice 0 no es tu cámara principal, cámbialo por 1 o 2
cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

print("Cámara iniciada. Presiona 'q' en la ventana para salir.")

while True:
    ret, frame = cam.read()
    if not ret:
        print("No se pudo capturar el fotograma.")
        break

    frame = cv2.flip(frame, 1)

    # 2. Definir y dibujar la Región de Interés (ROI)
    cv2.rectangle(frame, (200, 150), (400, 350), (0, 255, 0), 2)
    roi = frame[150:350, 200:400]

    # 3. Preprocesamiento MEJORADO para la CNN
    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Aplicar un pequeño desenfoque para eliminar el "ruido" de la cara o textura del papel
    desenfoque = cv2.GaussianBlur(gris, (5, 5), 0)

    # Usar el método de Otsu para calcular automáticamente la iluminación perfecta
    _, umbral = cv2.threshold(desenfoque, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # MOSTRAR ESTA VENTANA ES CRÍTICO: Aquí debes ver tu número blanco sobre fondo negro puro
    cv2.imshow("Lo que ve la IA", umbral)

    # Buscar formas (contornos) dentro de la imagen
    contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Solo proceder si encontramos algún contorno (evita leer el fondo vacío)
    if contornos:
        # Tomar el contorno más grande (asumimos que es el número dibujado)
        contorno_mayor = max(contornos, key=cv2.contourArea)

        # Si el objeto es lo suficientemente grande (ignorar manchas pequeñas)
        if cv2.contourArea(contorno_mayor) > 400:
            # Encontrar el rectángulo que encierra al número
            x, y, w, h = cv2.boundingRect(contorno_mayor)

            # Recortar solo el número (elimina el fondo alrededor)
            numero_recortado = umbral[y:y + h, x:x + w]

            # Redimensionar el recorte a 28x28 (el tamaño estricto de MNIST)
            numero_redimensionado = cv2.resize(numero_recortado, (28, 28), interpolation=cv2.INTER_AREA)

            # Normalizar para la red neuronal
            normalizado = numero_redimensionado / 255.0
            imagen_cnn = np.reshape(normalizado, (1, 28, 28, 1))

            # 4. Predicción
            prediccion = modelo.predict(imagen_cnn, verbose=0)
            digito = np.argmax(prediccion)
            confianza = np.max(prediccion)

            # 5. Envío de datos (Subimos la exigencia al 90% de confianza)
            if confianza > 0.90:
                cv2.putText(frame, f"Numero: {digito} ({confianza * 100:.1f}%)", (200, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Dibujar un rectángulo azul alrededor de lo que la IA está leyendo realmente
                cv2.rectangle(frame, (200 + x, 150 + y), (200 + x + w, 150 + y + h), (255, 0, 0), 1)

                if puerto and puerto.is_open:
                    puerto.write(str(digito).encode())

    # Mostrar la imagen a color
    cv2.imshow("Reconocimiento OpenCV", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
if puerto:
    puerto.close()