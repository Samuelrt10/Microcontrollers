# DOCUMENTO DE ESPECIFICACIÓN TÉCNICA Y MANUAL DE INGENIERÍA
# PROYECTO: Sistema Ciberfísico de Domótica para Terraza con Monitoreo Multivariable y Control Térmico Asistido por Inteligencia Artificial Local (Llama 3.1)

**Autores / Equipo de Ingeniería:**
* Samuel Rubio Tamberg (Cód: 7004288)
* Javier David León Delgado (Cód: 7004330)

---

## 1. RESUMEN EJECUTIVO Y JUSTIFICACIÓN DEL PROYECTO

### 1.1 Naturaleza del Proyecto
Este proyecto consiste en un **sistema ciberfísico y domótico de tiempo real** diseñado para la gestión integral de una terraza inteligente. El sistema resuelve tres necesidades de ingeniería en una única plataforma interconectada:
1. **Monitoreo energético renovable y auxiliar:** Adquisición de señales analógicas de generación fotovoltaica (panel solar) y mecánica (generador DC/dinamo).
2. **Cinemática y seguridad perimetral de accesos:** Medición de velocidad angular (RPM), detección de sentido de giro (apertura/cierre) y conteo de ciclos de una puerta batiente/corrediza sin fricción mecánica mediante odometría magnética en cuadratura.
3. **Control térmico inteligente por modulación de potencia (PWM):** Modulación de calor para un asador/parrilla mediante un actuador de potencia, comandado por un **agente de Inteligencia Artificial generativa local (Llama 3.1 8B)** que procesa órdenes en lenguaje natural capturadas por voz.

### 1.2 Justificación de la Arquitectura Distribuida (Edge vs. Host)
La implementación de Modelos de Lenguaje Grande (LLMs) requiere arquitecturas de hardware con alta capacidad de cómputo paralelo (GFLOPS) y gran ancho de banda de memoria (VRAM), características incompatibles con microcontroladores embebidos. Por tal motivo, se implementó una **arquitectura distribuida asíncrona maestro-esclavo**:
* **El Nodo Embebido (Edge - ESP32):** Se encarga exclusivamente de las tareas críticas y deterministas de tiempo real estricto: muestreo analógico (ADC), gestión de interrupciones externas por hardware (sensores Hall), control de ciclo de trabajo por modulación de ancho de pulso (PWM) y actualización de la pantalla local LCD vía bus I2C.
* **El Nodo de Procesamiento (Host PC):** Ejecuta la interfaz gráfica de usuario (GUI en Tkinter), el procesamiento digital de señales acústicas (STT - Speech to Text), la inferencia del modelo LLM (Llama 3.1 bajo el motor Ollama) y el motor determinista de respaldo por reglas léxicas (*Fallback Engine*).

---

## 2. ARQUITECTURA DE INTELIGENCIA ARTIFICIAL Y PROCESAMIENTO DE LENGUAJE NATURAL (NLP)

El cerebro de toma de decisiones del sistema recae en **Llama 3.1 (8B parámetros)**, ejecutado localmente para garantizar privacidad y latencia cero de red externa.

### 2.1 Arquitectura del Modelo Fundacional (Llama 3.1)
* **Red Neuronal Transformer:** El modelo utiliza una arquitectura de decodificador *Transformer* autorregresivo. Su principal ventaja para este proyecto es el mecanismo de **Atención de Consulta Agrupada (Grouped-Query Attention - GQA)**, que permite mantener un contexto largo (entendiendo instrucciones culinarias complejas) reduciendo significativamente la sobrecarga de memoria computacional durante la inferencia.
* **Cuantización (Quantization):** Para que un modelo de 8 billones de parámetros se ejecute eficientemente en la memoria RAM/VRAM de un PC estándar, el motor Ollama aplica técnicas de cuantización (usualmente a 4-bit u 8-bit, formato GGUF), reduciendo la precisión de los pesos de punto flotante (FP16 a INT4) con una pérdida casi nula de capacidad de razonamiento.
* **Ingeniería de Prompts (Zero-Shot Prompting):** Se utiliza una instrucción de sistema (*System Prompt*) altamente restrictiva. Se somete al modelo a un rol estricto ("Asistente Parrillero") y se le fuerza a realizar inferencia y clasificación simultánea (mapeando un texto natural a un nivel escalar del 0 al 4).

### 2.2 Forzado Estructural (JSON Mode)
Para garantizar la interoperabilidad entre el lenguaje natural y el código de control (Python), se utiliza el modo de salida estructurada de Ollama (`format="json"`). Esto bloquea las probabilidades de salida del modelo en la capa *Softmax* para que únicamente genere tokens válidos dentro de la gramática JSON, asegurando que la respuesta siempre pueda ser decodificada programáticamente sin romper el sistema.

---

## 3. INGENIERÍA DE COMUNICACIONES Y PROTOCOLOS

El sistema integra tres capas de comunicación distintas operando simultáneamente:

### 3.1 Comunicación Host-ESP32: UART (Universal Asynchronous Receiver-Transmitter)
* **Capa Física y Enlace:** Se utiliza un enlace serie asíncrono *full-duplex* a **115200 baudios**. 
* **Justificación del Baudrate y Trama:** A 115200 bps, con una trama `8-N-1` (1 bit de inicio, 8 de datos, sin paridad, 1 de parada = 10 bits por carácter), el sistema puede transmitir hasta 11,520 bytes por segundo. Dado que el comando de control del asador es una trama mono-byte ASCII (ej. `b'2\n'`), la latencia de transmisión es inferior a 0.1 milisegundos, garantizando un control "en tiempo real" percibido por el usuario.
* **Paradigma de Recepción:** Se utiliza un sondeo no bloqueante (`uart.any()`) en el ESP32 para evitar interrupciones de software que puedan desfasar la lectura de los sensores de la puerta.

### 3.2 Comunicación ESP32-LCD: Bus I2C (Inter-Integrated Circuit)
* **Protocolo:** Bus de comunicación síncrono *half-duplex* de dos hilos (SDA = `GPIO 21`, SCL = `GPIO 22`).
* **Configuración:** Opera en modo maestro con una frecuencia de reloj de $100\text{ kHz}$ (Modo Estándar). Se utiliza un expansor de E/S PCF8574T (dirección esclava `0x27`) para convertir la trama serial I2C en señales paralelas compatibles con el controlador HD44780 de la pantalla LCD.

### 3.3 Comunicación PC-Ollama: API REST (HTTP)
* **Protocolo de Capa de Aplicación:** El script de Python en el Host se comunica con el motor Ollama mediante peticiones HTTP POST a la interfaz de *loopback* (`http://localhost:11434`).
* **Ventaja:** Al ser *stateless* (sin estado), cada petición envía todo el historial de conversación (`historial_chat`) como contexto, lo que permite al modelo mantener la memoria de la interacción sin necesidad de almacenar variables de sesión complejas en el servidor local.

---

## 4. ESPECIFICACIÓN DETALLADA DE HARDWARE, SENSORES Y ACTUADORES

### 4.1 Cinemática de Puerta: Odometría en Cuadratura (Sensores Hall)
* **Principio Físico:** Dos sensores de efecto Hall unipolar/bipolar montados a 90° de desfase eléctrico respecto a un disco magnético multipolar en el eje de la puerta.
* **Discriminación de Sentido (Algoritmo de Estado):**
  Se asocia una interrupción de hardware por flanco de subida (`IRQ_RISING`) al Canal A (`GPIO 18`). En ese instante ($t_0$), se evalúa el nivel lógico del Canal B (`GPIO 19`):
  $$\text{Sentido} = \begin{cases} \text{Horario (Apertura)} & \text{si } \text{GPIO 19} == 0 \\ \text{Antihorario (Cierre)} & \text{si } \text{GPIO 19} == 1 \end{cases}$$
* **Filtrado Antirrebote (Debouncing):** Se implementa un filtro de software por histéresis temporal (`TIEMPO_ANTI_REBOTE_US = 1500`), ignorando interrupciones espurias causadas por vibraciones mecánicas de la puerta en un lapso de 1.5 milisegundos tras una detección válida.

### 4.2 Telemetría Energética Dual (Conversión ADC)
* **Muestreo de Señales:** Los pines `GPIO 34` y `GPIO 35` pertenecen al bloque `ADC1` del ESP32, seleccionado estratégicamente porque el bloque `ADC2` sufre conflictos de hardware cuando el módulo de radio (WiFi/Bluetooth) está activo.
* **Acondicionamiento y Cuantización:**
  Con atenuación de 11dB, el rango operativo es de $0$ a $3.3\text{V}$ con 12 bits de resolución (4096 pasos de cuantización). La ecuación característica para la reconstitución del voltaje antes del divisor resistivo ($R_1 = 10\text{ k}\Omega$, $R_2 = 4.7\text{ k}\Omega$) es:
  $$V_{\text{fuente}} = \left( \frac{\text{ADC}_{raw} \cdot 3.3}{4095} \right) \cdot \left( \frac{14.7\text{ k}\Omega}{4.7\text{ k}\Omega} \right)$$

### 4.3 Control Térmico Proporcional (PWM para Asador)
El control de la etapa de potencia se realiza conmutando una señal cuadrada (`GPIO 25`) a una frecuencia fija de $1000\text{ Hz}$. El porcentaje de energía entregada al asador (o simulada en LEDs) responde a la modulación del ciclo de trabajo (*Duty Cycle*) de 10 bits ($0 - 1023$):

| Nivel | Estado Térmico | Ciclo de Trabajo (%) | Valor PWM (10-bit) | Aplicación / Justificación Termodinámica |
|:---:|:---|:---:|:---:|:---|
| **0** | **Standby** | 0.0% | `duty(0)` | Asador inactivo, seguro para mantenimiento. |
| **1** | **Mantenimiento** | 25.0% | `duty(256)` | Mantener temperatura por encima de la zona de peligro biológico (60°C). |
| **2** | **Medio-Bajo** | 50.0% | `duty(512)` | Cocción lenta (embutidos) para asegurar temperatura interna segura sin carbonizar exterior. |
| **3** | **Medio-Alto** | 75.0% | `duty(768)` | Cocción estándar mediante transferencia de calor convectiva y radiante equilibrada. |
| **4** | **Sellado Máximo** | 100.0% | `duty(1023)` | Sellado superficial, activando la Reacción de Maillard mediante alta transferencia térmica inicial. |

---

## 5. MECANISMO DE TOLERANCIA A FALLOS (FALLBACK DETERMINISTA)

Los sistemas ciberfísicos que dependen de IA deben ser deterministas en sus rutinas de fallo. Si el modelo LLM excede un *timeout* de 18 segundos, o la red local colapsa, la aplicación host ejecuta una **Máquina de Inferencia Léxica (Fallback Engine)** de tiempo constante ($O(1)$).

El algoritmo escanea la entrada de voz transcrita contra matrices de expresiones regulares precompiladas:
```python
# Extracto Lógico del Motor Determinista
if any(k in input for k in ["sellar", "tomahawk", "fuego maximo"]): return 4
elif any(k in input for k in ["carne", "hamburguesa", "corte"]): return 3
elif any(k in input for k in ["chorizo", "pollo", "medio"]): return 2
elif any(k in input for k in ["apagar", "cero", "terminar"]): return 0