# Actividad 6 - Punto 1: Sistema Robótico Dibujante con Teclado Matricial 4x4 y PyBullet

**Universidad Militar Nueva Granada**  
**Facultad de Ingeniería — Microcontroladores**  
**Autor:** Samuel Rubio Tamberg  

**Objetivo:** Integrar un sistema embebido con teclado matricial 4x4 y pantalla LCD I2C a una simulación de brazo robótico en PyBullet utilizando visión artificial con OpenCV y cinemática inversa.

---

## 1. Descripción del Proyecto

El sistema implementa una arquitectura **Real-to-Sim**:
1. El usuario presiona una tecla en un **teclado matricial 4x4** conectado a una **ESP32**.
2. La ESP32 muestra el carácter en una **pantalla LCD 16x2 I2C** y lo transmite por **puerto serial (UART)** al computador.
3. El script de Python en el computador procesa la plantilla del carácter con **OpenCV**.
4. Un modelo de **brazo robótico en formato URDF** simula en **PyBullet** el trazado milimétrico del carácter sobre una mesa de dibujo mediante **Cinemática Inversa**.

```
[Teclado 4x4] ---> [ESP32] ---> [LCD 16x2 I2C]
                     | (Serial 9600 baud)
                     v
             [Python / PC]
             ├── OpenCV (Plantillas y Trazos)
             └── PyBullet (Cinemática Inversa y Simulación 3D)
```

---

## 2. Diagrama de Conexiones de Hardware (ESP32)

### A. Teclado Matricial 4x4
| Pin Teclado | Función | GPIO ESP32 | Modo |
|:---:|:---:|:---:|:---:|
| **Fila 1 (R1)** | Fila 1 | **GPIO 19** | Salida digital |
| **Fila 2 (R2)** | Fila 2 | **GPIO 18** | Salida digital |
| **Fila 3 (R3)** | Fila 3 | **GPIO 5**  | Salida digital |
| **Fila 4 (R4)** | Fila 4 | **GPIO 17** | Salida digital |
| **Col 1 (C1)**  | Columna 1 | **GPIO 16** | Entrada con Pull-Down |
| **Col 2 (C2)**  | Columna 2 | **GPIO 4**  | Entrada con Pull-Down |
| **Col 3 (C3)**  | Columna 3 | **GPIO 2**  | Entrada con Pull-Down |
| **Col 4 (C4)**  | Columna 4 | **GPIO 15** | Entrada con Pull-Down |

### B. Pantalla LCD 16x2 con Módulo I2C
| Pin LCD I2C | Función | GPIO ESP32 | Notas |
|:---:|:---:|:---:|:---:|
| **GND** | Tierra | **GND** | Masa común |
| **VCC** | Alimentación | **VIN / 5V** | 5V para contraste óptimo |
| **SDA** | Datos I2C | **GPIO 21** | Bus de datos |
| **SCL** | Reloj I2C | **GPIO 22** | Bus de reloj |

---

## 3. Estructura de Archivos del Proyecto

```text
Actividad_6/6.1/
├── main.py                 # Programa principal (PyBullet + OpenCV + Serial)
├── brazo_robot.urdf        # Modelo cinemático y geométrico del brazo robótico
├── README.md               # Documentación técnica del proyecto
├── main_esp/
│   └── main_esp.ino        # Firmware para ESP32 en Arduino C++
└── imagenes/               # Plantillas de las 16 teclas (300x300 px)
    ├── 0.png ... 9.png     # Teclas numéricas 0 al 9
    ├── A.png ... D.png     # Teclas alfabéticas A, B, C, D
    ├── asterisco.png       # Tecla '*' (nombre compatible con Windows)
    └── numeral.png         # Tecla '#' (nombre compatible con Windows)
```

---

## 4. Aspectos Técnicos de la Implementación

### A. Cobertura Total de Teclas (16/16)
Se implementó el soporte completo para las 16 teclas de la matriz:
- **Numéricas:** `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`.
- **Comandos:** `A`, `B`, `C`, `D`.
- **Especiales:** `*` (guardado como `asterisco.png`) y `#` (guardado como `numeral.png`).

### B. Cinemática Inversa Analítica Exacta
- Se implementó la solución analítica geométrica para las articulaciones rotacionales del robot (`joint_1` yaw, `joint_2` pitch, `joint_3` pitch), eliminando mínimos locales o errores numéricos ($\text{error} < 0.001\text{ mm}$).
- **Espacio de Trabajo Calibrado:**
  - Centro del dibujo: $X = 0.35\text{ m}$, $Y = 0.00\text{ m}$.
  - Altura de contacto (mesa): $Z = 0.40\text{ m}$.
  - Altura de desplazamiento en el aire: $Z = 0.46\text{ m}$.
  - Tamaño de caracteres: $12\text{ cm} \times 12\text{ cm}$.

### C. Algoritmo de Trazado con Levantamiento de Pluma (*Pen-Up / Pen-Down*)
Para caracteres con trazos discontinuos (como `4`, `7`, `A`, `B`, `D`, `*`, `#`), el efector final:
1. Se traslada por el aire ($Z = 0.46\text{ m}$) hasta el origen del trazo.
2. Desciende al papel ($Z = 0.40\text{ m}$) y traza la trayectoria en rojo con interpolación suave.
3. Se levanta nuevamente al finalizar el trazo para evitar líneas cruzadas no deseadas.
4. Al culminar el carácter, regresa a una postura de reposo elevada que deja visible el dibujo completo.

---

## 5. Instrucciones de Ejecución

### Requisitos Previos
Tener instaladas las dependencias en el entorno virtual (`pybullet`, `opencv-python`, `pyserial`, `numpy`).

### Paso 1: Conectar Hardware
- Conectar la ESP32 al puerto USB de la computadora.
- Subir `main_esp/main_esp.ino` desde el **Arduino IDE** y cerrar el Monitor Serie para liberar el puerto COM.

### Paso 2: Ejecutar la Simulación
Ejecutar el script principal desde la terminal:
```bash
python main.py
```
*(O si te encuentras en la raíz del repositorio: `python Actividad_6/6.1/main.py`)*

### Paso 3: Interactuar con el Sistema
El sistema admite tres métodos de entrada simultáneos:
1. **Teclado físico 4x4:** Presionar cualquier tecla en el circuito físico.
2. **Ventana de PyBullet:** Hacer clic sobre la ventana 3D y pulsar las teclas del computador (`0-9`, `A-D`, `*`, `#`).
3. **Consola interactiva:** Escribir el carácter en la terminal y presionar `Enter`.

---

## 6. Demostración y Validación en Video

> [!NOTE]
> Enlace al video de sustentación y demostración práctica donde se evidencia la interacción con el teclado matricial 4x4, la visualización en la pantalla LCD 16x2 I2C, la transmisión por UART y la simulación 3D en PyBullet del brazo robótico trazando caracteres mediante cinemática inversa:
>
> 🔗 **Video Demostrativo (YouTube):** [ENLACE_AL_VIDEO_AQUÍ](https://youtu.be/MAtFgYUBsx8)

---

## 7. Información Institucional

- **Estudiante:** Samuel Rubio Tamberg
- **Institución:** Universidad Militar Nueva Granada
- **Facultad:** Facultad de Ingeniería
- **Asignatura:** Microcontroladores
