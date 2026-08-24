# Sistema de Automatización para Terraza con Asador IA

Este proyecto es un sistema de domótica para una terraza. Monitoriza la generación de energía (solar y DC), mide el movimiento de una puerta y controla el nivel de calor de un asador inteligente mediante comandos de voz procesados por una IA local.

## Resumen del Código

El sistema funciona con dos programas que trabajan en conjunto:

1. **MicroPython (ESP32):** Es el hardware en la terraza. 
   * **Lee sensores:** Usa 2 sensores Hall (en cuadratura) para calcular la velocidad (RPM) y dirección de una puerta. Lee 2 ADCs para medir la potencia (mW) de un panel solar y un generador DC.
   * **Muestra datos:** Imprime las RPM y la potencia en una pantalla LCD 1602 vía I2C.
   * **Controla el Asador:** Escucha el puerto Serial esperando un número (0 al 4) para ajustar el PWM de los LEDs que simulan/controlan el calor del asador.

2. **Python (PC / Tkinter):** Es el cerebro de IA y la interfaz gráfica.
   * Graba la voz del usuario y la transcribe a texto.
   * Envía el texto a **Llama 3.1 (Ollama)** para decidir qué nivel de calor necesita la comida.
   * Envía el comando final al ESP32 y muestra la conversación en la pantalla.

---

## ¿Cómo se comunican el sistema y la IA?

El flujo de comunicación conecta el hardware (ESP32), la computadora (Python) y la Inteligencia Artificial (Llama 3.1) en 4 pasos:

1. **Captura (Usuario ➔ PC):** El usuario habla por el micrófono (ej. *"Voy a asar unos chorizos"*). Python transcribe el audio a texto usando `SpeechRecognition`.
2. **Inferencia IA (PC ➔ Llama 3.1 ➔ PC):** 
   * Python empaqueta el texto y hace una petición HTTP (`requests.post`) a la API local de **Ollama** (puerto `11434`). 
   * Llama 3.1 evalúa el texto bajo un "prompt de sistema" que le exige responder obligatoriamente en formato JSON.
   * Llama responde: `{"respuesta": "Nivel 2 para cocción pareja.", "nivel_sugerido": 2}`.
3. **Comando Serial (PC ➔ ESP32):** Python lee el número `2` del JSON y lo envía por cable USB (Puerto COM / Serial) al ESP32.
4. **Acción Física (ESP32 ➔ Asador):** El ESP32 recibe el número `2` por Serial y ajusta el nivel PWM de los LEDs (o encendedores) al instante, sin interrumpir la lectura de la puerta ni de los generadores.

*(Nota: Si la IA tarda demasiado o falla, el código en Python tiene un sistema de respaldo que busca palabras clave en el texto para asegurar que el asador siempre responda rápido).*

---

## Requisitos y Uso

**Hardware:** ESP32, Pantalla LCD 1602 (I2C), 2x Sensores Hall, Panel Solar, Motor DC (Generador), LEDs/Relés para asador, Micrófono en PC.
**Software:** 
* Python 3.8+ (`pip install pyserial requests numpy sounddevice SpeechRecognition`).
* Ollama corriendo localmente con el modelo Llama 3.1 (`ollama run llama3.1:8b`).

**Ejecución:**
1. Carga el firmware MicroPython en el ESP32.
2. Abre Ollama en tu PC.
3. Ejecuta el script de Python, selecciona el puerto COM de tu ESP32 y conéctalo.
4. Usa el micrófono o la barra manual para controlar el asador mientras el ESP32 muestra los datos de la terraza en el LCD.