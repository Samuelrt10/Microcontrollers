# ESP-WROOM-32 (ESP32): Guía Técnica y Documentación

Bienvenido a la documentación técnica básica del módulo ESP-WROOM-32. Este archivo `README.md` consolida la información esencial sobre su arquitectura, características de hardware y una comparativa de los entornos de desarrollo más populares.

---

## 1. Definición y Arquitectura

El **ESP-WROOM-32** es un potente módulo de microcontrolador (SoC - System on a Chip) de bajo costo y bajo consumo de energía, desarrollado por Espressif Systems. Es ampliamente utilizado en proyectos de IoT (Internet de las Cosas), robótica y domótica gracias a su integración nativa de conectividad Wi-Fi y Bluetooth.

### Estructura Interna
*   **Microprocesador:** Tensilica Xtensa Dual-Core de 32 bits (LX6).
*   **Frecuencia de reloj:** Ajustable entre 160 MHz y 240 MHz.
*   **Memoria:** 
    *   ROM: 448 KB (para arranque y funciones del núcleo).
    *   SRAM: 520 KB (para datos e instrucciones).
    *   Memoria Flash Externa: Típicamente de 4 MB a 16 MB (dependiendo del fabricante de la placa de desarrollo).
*   **Arquitectura Harvard modificada:** Utiliza buses separados para instrucciones y datos, lo que permite un acceso más rápido a la memoria.
*   **Co-procesador de ultra bajo consumo (ULP):** Permite que el chip principal entre en un estado de suspensión profunda (Deep Sleep) mientras el co-procesador sigue monitoreando sensores, consumiendo apenas unos microamperios.

---

## 2. Características, Conexiones y Periféricos

El módulo destaca por su versatilidad en la multiplexación de pines. Casi cualquier pin GPIO (General Purpose Input/Output) puede ser configurado mediante software para realizar múltiples funciones.

### Pines y Conexiones Principales
El ESP32 cuenta con hasta 34 pines GPIO configurables. Soporta múltiples protocolos de comunicación por hardware, incluyendo:
*   **3x UART** (Universal Asynchronous Receiver-Transmitter)
*   **3x SPI** (Serial Peripheral Interface)
*   **2x I2C** (Inter-Integrated Circuit)
*   **2x I2S** (Para procesamiento de audio)
*   **CAN Bus 2.0**

### Capacidades Analógicas y Modulación
| Periférico | Cantidad/Resolución | Descripción |
| :--- | :--- | :--- |
| **ADC** (Convertidor Analógico a Digital) | 18 Canales / 12 bits | Permite leer voltajes analógicos con valores entre 0 y 4095. Es importante notar que el ADC del ESP32 no es completamente lineal en los extremos de medición. |
| **DAC** (Convertidor Digital a Analógico) | 2 Canales / 8 bits | Ubicados en los pines GPIO 25 y 26, permiten generar voltajes analógicos reales (no simulados por PWM) para señales de audio o control. |
| **PWM** (Modulación por Ancho de Pulso) | 16 Canales independientes | No está limitado a pines específicos por hardware. Se puede asignar un canal PWM a casi cualquier GPIO para controlar servomotores, brillo de LEDs o velocidad de motores. |
| **Sensores Capacitivos** | 10 Canales | Pines sensibles al tacto que detectan variaciones en la capacitancia eléctrica (Touch pins). |

---

## 3. Entornos de Programación: C/C++ vs. MicroPython

El ESP32 puede ser programado en múltiples lenguajes. A continuación, se contrastan las dos opciones más utilizadas: **C/C++** (usando ESP-IDF o el IDE de Arduino) y **MicroPython**.

### C / C++ (Arduino IDE o ESP-IDF)
Es el estándar de la industria para desarrollo de sistemas embebidos y productos finales.

**Ventajas:**
*   **Rendimiento máximo:** El código compilado se ejecuta directamente en el procesador con la mayor velocidad posible.
*   **Control de hardware:** Acceso total a los registros de bajo nivel y a la gestión del sistema operativo en tiempo real (FreeRTOS) que corre en los dos núcleos.
*   **Ecosistema masivo:** Existe una biblioteca de C/C++ para prácticamente cualquier sensor o actuador del mercado.
*   **Eficiencia de memoria:** Gestión manual y optimizada de la RAM y la memoria Flash.

**Desventajas:**
*   **Curva de aprendizaje:** La sintaxis es más estricta y la gestión de memoria (punteros, fugas de memoria) puede ser compleja.
*   **Tiempos de compilación:** Cada cambio en el código requiere recompilar y subir el binario completo, lo que hace el proceso de prueba más lento.

### MicroPython
Una implementación eficiente de Python 3 diseñada específicamente para microcontroladores.

**Ventajas:**
*   **Desarrollo ultrarrápido (Prototipado):** La sintaxis limpia de Python permite escribir lógica compleja en pocas líneas de código.
*   **No requiere compilación:** Al ser interpretado, puedes usar el REPL (Read-Eval-Print Loop) para ejecutar comandos en vivo directamente en la placa mediante consola.
*   **Facilidad de uso:** Excelente para pruebas de concepto, análisis de datos en la placa y manejo de cadenas de texto o JSON (muy útil para IoT).

**Desventajas:**
*   **Menor velocidad de ejecución:** Al ser un lenguaje interpretado, es significativamente más lento que C, lo que puede ser un problema para procesos matemáticos intensivos o tiempos críticos de microsegundos.
*   **Mayor consumo de recursos:** El intérprete de MicroPython ocupa espacio en la memoria Flash y consume más RAM operativa.
*   **Acceso limitado a bajo nivel:** No todas las características de hardware avanzadas del ESP32 están expuestas o son fácilmente manejables desde MicroPython.
