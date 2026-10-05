# Actividad 6 - Punto 2: Reconocimiento de Dígitos Manuscritos con Visión Artificial (CNN) y Comunicación Maestro-Esclavo (UART + SPI)

**Universidad Militar Nueva Granada**  
**Facultad de Ingeniería — Microcontroladores**  
**Autor:** Samuel Rubio Tamberg  

**Objetivo:** Desarrollar un sistema embebido inteligente que capture dígitos escritos a mano mediante una cámara web, los clasifique en tiempo real utilizando una Red Neuronal Convolucional (CNN) entrenada sobre el dataset MNIST, y transmita el resultado a un microcontrolador ESP32-S3 Maestro por UART para su retransmisión a un dispositivo Esclavo mediante el bus SPI.

---

## 1. Arquitectura General del Sistema

El proyecto integra visión computacional, aprendizaje profundo (*Deep Learning*) y protocolos de comunicación industrial/embebida en una arquitectura jerárquica de 3 niveles:

```
+-----------------------------------------------------------------------------------+
|                                     NIVEL 1: PC                                   |
|                                                                                   |
|  [Cámara Web] ---> [OpenCV: ROI + Filtro Gauss + Otsu]                            |
|                                   |                                               |
|                                   v                                               |
|               [CNN Keras/TensorFlow (MNIST Model)]                                |
|                                   |                                               |
|                                   v  (Filtro Confianza > 90%)                     |
|                           [Puerto Serial UART]                                    |
+-----------------------------------|-----------------------------------------------+
                                    | Cable USB (COM / 9600 baud)
                                    v
+-----------------------------------------------------------------------------------+
|                            NIVEL 2: ESP32-S3 MAESTRO                              |
|                                                                                   |
|  Recepción UART ---> Decodificación de Dígito ---> Empaquetado SPI                |
+-----------------------------------|-----------------------------------------------+
                                    | Bus SPI (SCK, MOSI, MISO, CS @ 100 kHz)
                                    v
+-----------------------------------------------------------------------------------+
|                               NIVEL 3: ESCLAVO SPI                                |
|                                                                                   |
|  Recepción y procesamiento de datos para actuación / visualización                |
+-----------------------------------------------------------------------------------+
```

---

## 2. Red Neuronal Convolucional (CNN - Dataset MNIST)

### A. Arquitectura del Modelo (`entrenar_modelo.py`)
Para garantizar una alta precisión y robustez frente a diferentes estilos de escritura, se implementó una red convolucional secuencial con la siguiente estructura:

| Capa | Tipo | Dimensiones de Salida | Función de Activación | Descripción |
|:---:|:---:|:---:|:---:|:---|
| **Input** | Imagen monocromática | `(28, 28, 1)` | - | Entrada normalizada en el rango $[0, 1]$ |
| **Capa 1** | `Conv2D (32 filtros, 3x3)` | `(26, 26, 32)` | ReLU | Detección de características primarias (bordes, esquinas y trazos) |
| **Capa 2** | `MaxPooling2D (2x2)` | `(13, 13, 32)` | - | Reducción espacial y conservación de características invariantes |
| **Capa 3** | `Conv2D (64 filtros, 3x3)` | `(11, 11, 64)` | ReLU | Extracción de patrones de mayor complejidad (curvas, bucles e intersecciones) |
| **Capa 4** | `MaxPooling2D (2x2)` | `(5, 5, 64)` | - | Segunda reducción de dimensionalidad |
| **Capa 5** | `Flatten` | `(1600)` | - | Vectorización de mapas de características |
| **Capa 6** | `Dense (64 neuronas)` | `(64)` | ReLU | Capa densa de interpretación y combinación de características |
| **Output** | `Dense (10 neuronas)` | `(10)` | Softmax | Distribución de probabilidad para cada dígito (`0` al `9`) |

### B. Parámetros de Entrenamiento
- **Dataset:** MNIST oficial (60,000 imágenes de entrenamiento, 10,000 imágenes de validación).
- **Optimizador:** `Adam` (tasa de aprendizaje adaptativa).
- **Función de Pérdida:** `sparse_categorical_crossentropy`.
- **Métricas:** Exactitud (*Accuracy*) superior al **98.5%** en 5 épocas.
- **Archivo Resultante:** `mnist_model.h5`.

---

## 3. Procesamiento de Visión Artificial en Tiempo Real (`main.py`)

Para que la red neuronal reconozca correctamente números dibujados en el mundo real, la imagen capturada por la cámara debe coincidir con el formato canónico de MNIST (fondo negro puro, trazo blanco centrado de $28 \times 28$ píxeles).

```
   Frame de Cámara
+---------------------+
|                     |
|     +---------+     |        1. Conversión BGR a Escala de Grises
|     |  [ROI]  |     |   -->  2. Filtro Gaussiano (5x5, eliminación de ruido)
|     |    5    |     |   -->  3. Umbralización Otsu Inversa (Fondo negro, trazo blanco)
|     +---------+     |   -->  4. Detección de Contornos (Bounding Box del dígito)
|                     |   -->  5. Recorte + Escalado a 28x28 + Normalización [0, 1]
+---------------------+   -->  6. Inferencia CNN (Confianza > 90%)
```

### Etapas del Algoritmo:
1. **Captura DirectShow:** Uso de `cv2.CAP_DSHOW` para evitar bloqueos y pantallas negras en sistemas operativos Windows.
2. **Región de Interés (ROI):** Delimitada en un marco de $200 \times 200$ píxeles (`x: 200 a 400`, `y: 150 a 350`) para aislar el número del entorno.
3. **Filtro Gaussiano:** Suavizado con kernel de $5 \times 5$ que elimina imperfecciones del papel y ruido del sensor óptico.
4. **Binarización de Otsu (`THRESH_BINARY_INV + THRESH_OTSU`):** Calcula automáticamente el umbral óptimo de luz sin requerir calibración manual ante cambios de iluminación.
5. **Detección y Recorte de Contorno:** Mediante `cv2.findContours` y `cv2.boundingRect`, se localiza el dígito, se aísla de los bordes vacíos y se escala exactamente a $28 \times 28$ píxeles mediante interpolación de área (`cv2.INTER_AREA`).
6. **Filtrado por Umbral de Confianza:** La predicción solo se acepta y transmite si la probabilidad es **superior al 90%** (`confianza > 0.90`), evitando lecturas erróneas por sombras o ruido transitorio.

---

## 4. Hardware y Comunicaciones Embebidas

### A. Firmware del ESP32-S3 Maestro (`maestro/maestro.ino`)
El microcontrolador maestro opera como un puente (*bridge*) de comunicación:
1. Escucha de forma continua el puerto serie `Serial` (UART) conectado a la PC a **9600 baudios**.
2. Al recibir un carácter numérico, inicia una transacción SPI con el esclavo.
3. Habilita la línea Chip Select (`CS` en nivel bajo `LOW`), transfiere el byte a una velocidad estable de **100 kHz** en modo 0 (`SPI_MODE0`), y restablece `CS` en nivel alto `HIGH`.

### B. Asignación de Pines del Bus SPI (ESP32-S3)

| Pin ESP32-S3 | Señal SPI | Dirección | Descripción |
|:---:|:---:|:---:|:---|
| **GPIO 10** | `S3_CS`   | Salida (Maestro $\to$ Esclavo) | Selección de Chip / Esclavo (Activo en bajo) |
| **GPIO 11** | `S3_MOSI` | Salida (Maestro $\to$ Esclavo) | Salida de datos del Maestro hacia el Esclavo |
| **GPIO 12** | `S3_SCK`  | Salida (Maestro $\to$ Esclavo) | Señal de reloj sincronizada generada por el Maestro |
| **GPIO 13** | `S3_MISO` | Entrada (Esclavo $\to$ Maestro) | Retorno de datos desde el Esclavo (opcional) |
| **GND**     | `GND`     | Común                          | Referencia de tierra compartida entre dispositivos |

---

## 5. Estructura de Archivos del Proyecto

```text
Actividad_6/6.2/
├── README.md               # Documentación técnica completa para la entrega
├── main.py                 # Pipeline de visión por computador, inferencia y envío UART
├── entrenar_modelo.py      # Script de entrenamiento de la CNN sobre el dataset MNIST
├── mnist_model.h5          # Modelo entrenado listo para inferencia (red compilada)
└── maestro/
    └── maestro.ino         # Código fuente de Arduino para el ESP32-S3 Maestro (SPI)
```

---

## 6. Guía de Ejecución y Pruebas

### Paso 1: Subir el Firmware al ESP32-S3
1. Abrir `maestro/maestro.ino` en el **Arduino IDE**.
2. Seleccionar la placa **ESP32S3 Dev Module** (o equivalente).
3. Compilar y subir el programa al microcontrolador.
4. Cerrar el Monitor Serie de Arduino para no bloquear el puerto COM.

### Paso 2: Configuración del Puerto en Python
En la línea 8 de `main.py`, verificar que el puerto coincida con el asignado al ESP32-S3 en el Administrador de Dispositivos (por defecto `'COM10'`):
```python
puerto = serial.Serial('COM10', 9600, timeout=1)
```

### Paso 3: Ejecutar el Sistema de Visión Artificial
Ejecutar el script principal desde la terminal:
```bash
python main.py
```
*(O si te encuentras en la raíz del repositorio: `python Actividad_6/6.2/main.py`)*

### Paso 4: Presentación de Dígitos
1. Se abrirán dos ventanas en pantalla:
   - **`Reconocimiento OpenCV`:** Vista general a color con el cuadro verde de la ROI.
   - **`Lo que ve la IA`:** Vista procesada en blanco y negro (el dígito debe verse blanco sobre fondo negro puro).
2. Dibujar un número (del `0` al `9`) con marcador negro sobre una hoja blanca (o mostrarlo desde la pantalla de un celular) y colocarlo dentro del recuadro verde.
3. Al alcanzar una confianza $\ge 90\%$, el sistema mostrará el número reconocido en verde y transmitirá instantáneamente el byte a la ESP32-S3 vía serial para su propagación por el bus SPI.
4. Para finalizar la ejecución, presionar la tecla **`q`** sobre la ventana de video.

---

## 7. Demostración y Validación en Video

> [!NOTE]
> Enlace al video de sustentación y demostración práctica donde se evidencia la captura en vivo con la cámara web, el preprocesamiento con OpenCV, la clasificación en tiempo real con la CNN (MNIST), la comunicación UART hacia el ESP32-S3 y la transmisión al esclavo mediante el bus SPI:
>
> 🔗 **Video Demostrativo (YouTube):** [ENLACE_AL_VIDEO_AQUÍ](https://youtu.be/oJddQ3Drf8Y)

---

## 8. Información Institucional

- **Estudiante:** Samuel Rubio Tamberg
- **Institución:** Universidad Militar Nueva Granada
- **Facultad:** Facultad de Ingeniería
- **Asignatura:** Microcontroladores
