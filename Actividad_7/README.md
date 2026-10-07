# 🐜 Práctica Real-to-Sim: Algoritmo ACO Distribuido (ESP32 + PyBullet)

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-Hardware-red?style=for-the-badge&logo=espressif&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-blue?style=for-the-badge&logo=docker&logoColor=white)
![PyBullet](https://img.shields.io/badge/PyBullet-Simulation-orange?style=for-the-badge)

## 📋 Tabla de Contenidos
1. [Información General](#1-información-general)
2. [Descripción General del Proyecto](#2-descripción-general-del-proyecto)
3. [Estructura del Repositorio](#3-estructura-del-repositorio)
4. [Arquitectura del Sistema](#4-arquitectura-del-sistema)
5. [Fundamento Matemático (ACO)](#5-fundamento-matemático-aco)
6. [Requisitos e Instalación](#6-requisitos-e-instalación)
7. [Instrucciones de Ejecución](#7-instrucciones-de-ejecución)
8. [Demostración en Video](#8-demostración-en-video)

---

## 1. 🎓 Información General

| Campo | Detalle |
| :--- | :--- |
| **Institución** | Universidad Militar Nueva Granada |
| **Programa** | Ingeniería Mecatrónica |
| **Estudiante** | Samuel Rubio Tamberg |
| **Código** | 7004288 |
| **Entorno de Simulación** | Python 3.10+, PyBullet, Docker |
| **Hardware de Control** | Enjambre heterogéneo (ESP32 Estándar, ESP32-S3, ESP32-S3 Super Mini) |

---

## 2. 💡 Descripción General del Proyecto

Este repositorio contiene la implementación de un esquema de interacción física **Real-to-Sim**, donde interfaces de hardware basadas en microcontroladores ESP32 comandan dinámicamente una simulación robótica en tiempo real.

El proyecto se centra en la ejecución distribuida del algoritmo bioinspirado **ACO (Optimización por Colonia de Hormigas)** sobre una topología de red WiFi ad-hoc, resolviendo la navegación en un laberinto con visualización concurrente en un gemelo digital.

---

## 3. 📂 Estructura del Repositorio

```text
Actividad_7/
│
├── esp_code/
│   └── esp_code.ino        # Código en C++ para los nodos ESP32
│
├── digital_twin.py         # Script principal del Gemelo Digital en PyBullet
├── Dockerfile              # Configuración de Docker para el entorno de simulación
└── README.md               # Documentación del proyecto (este archivo)
```

---

## 4. ⚙️ Arquitectura del Sistema

* **Objetivo:** Tres nodos ESP32 ejecutan el algoritmo de Optimización por Colonia de Hormigas (ACO) de manera distribuida, transmitiendo su estado a un gemelo digital en PyBullet encapsulado en un contenedor de Docker.
* **Red Inalámbrica y Comunicación:** 
  * **Nodo 0 (ESP32 Clásico):** Actúa como Access Point (`ACO_SWARM_NET`).
  * **Nodo 1 (ESP32-S3) & Nodo 2 (ESP32-S3 Super Mini):** Actúan como estaciones (STA).
  * Los agentes intercambian la matriz de feromonas y su posición mediante mensajes UDP Broadcast (puerto 4210).
* **Gemelo Digital (PyBullet):** Un script en Python (`digital_twin.py`) recibe la telemetría UDP (`POS,id,x,y`) y actualiza la cinemática de los agentes virtuales en tiempo real, demostrando la exploración y convergencia colectiva hacia la ruta óptima.

---

## 5. 🧮 Fundamento Matemático (ACO)

El éxito de la **Optimización por Colonia de Hormigas (ACO)** radica en el equilibrio entre la exploración probabilística y la comunicación indirecta o *estigmergia* (mediante feromonas). Las ecuaciones que rigen el comportamiento de nuestro enjambre de ESP32 son las siguientes:

### 5.1. Regla de Transición Probabilística
Cuando una hormiga (o nodo en el ESP32) $k$ se encuentra en el punto $i$, la probabilidad $P_{ij}^k$ de moverse al siguiente punto $j$ se define como:

$$ P_{ij}^k = \frac{[\tau_{ij}]^\alpha [\eta_{ij}]^\beta}{\sum_{l \in N_i^k} [\tau_{il}]^\alpha [\eta_{il}]^\beta} $$

*   **$\tau_{ij}$:** Nivel de feromona actual en el camino entre $i$ y $j$ (representa la *experiencia colectiva*).
*   **$\eta_{ij}$:** Información heurística del camino, usualmente proporcional al inverso de la distancia ($1/d_{ij}$). Aporta *conocimiento local* previo.
*   **$\alpha$:** Parámetro que pondera la importancia de la feromona (tendencia a la **explotación** de rutas descubiertas).
*   **$\beta$:** Parámetro que pondera la importancia de la distancia/heurística (tendencia a la **exploración** hacia caminos cortos).
*   **$N_i^k$:** Conjunto de nodos viables/vecinos aún no visitados por la hormiga $k$.

### 5.2. Regla de Actualización de Feromonas
Una vez que las hormigas finalizan su recorrido por el laberinto o grafo, el mapa de feromonas se actualiza globalmente según la ecuación:

$$ \tau_{ij} \leftarrow (1 - \rho) \tau_{ij} + \sum_{k=1}^m \Delta \tau_{ij}^k $$

*   **$\rho$:** Tasa de evaporación de la feromona ($0 < \rho \le 1$). La evaporación es crucial para evitar que el algoritmo se estanque rápidamente en mínimos locales (rutas subóptimas).
*   **$m$:** Número total de agentes explorando (en nuestro caso, los nodos ESP32).
*   **$\Delta \tau_{ij}^k$:** Cantidad de feromona depositada por la hormiga $k$ en el segmento $(i,j)$. Se calcula como $\Delta \tau_{ij}^k = Q / L_k$ si la hormiga pasó por ahí (donde $Q$ es una constante y $L_k$ es la longitud/costo total de su ruta). Si no pasó, el valor es $0$.

### 5.3. Convergencia del Enjambre
Dado que las rutas más cortas (menor $L_k$) se completan más rápido y depositan una mayor cantidad de feromonas ($Q/L_k$), su nivel de $\tau$ crece frente a las rutas largas que sufren más los efectos de la evaporación $\rho$. Por retroalimentación positiva, la probabilidad $P_{ij}$ de los segmentos óptimos tenderá a $1$, lo que provoca que todos los nodos ESP32 eventualmente coincidan en la misma solución.

---

## 6. 🛠️ Requisitos e Instalación

### Entorno Docker (Recomendado)
Se requiere **Docker Desktop** y un servidor de entorno gráfico X11 (**VcXsrv** en Windows) para visualizar la simulación de PyBullet.

1. Instala y configura **XLaunch (VcXsrv)** habilitando `Multiple windows`, `Start no client` y marcando la casilla obligatoria **"Disable access control"**.
2. Construye la imagen desde la raíz del proyecto (`Actividad_7/`):
```bash
docker build -t pybullet-aco-twin .
```

### Entorno Local (Alternativa)
Si deseas correr el gemelo digital sin Docker, instala las dependencias en tu entorno Python:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install pybullet numpy
```

---

## 7. 🚀 Instrucciones de Ejecución

### 7.1. Configuración del Hardware (ESP32)
1. **Conectar los ESP32** vía USB al computador.
2. **Cargar el firmware** (`esp_code/esp_code.ino`) utilizando el IDE de Arduino en los tres microcontroladores correspondientes.
3. **Energizar el Nodo 0** para desplegar la red WiFi (`ACO_SWARM_NET`).
4. **Energizar los Nodos 1 y 2**. Los nodos comenzarán a comunicarse automáticamente.

### 7.2. Ejecución del Gemelo Digital
#### Opción A: Usando Docker
Levanta el Gemelo Digital redirigiendo la pantalla al servidor X11 local (reemplazar `host.docker.internal` por tu IP local si es necesario):
```bash
docker run -it --rm -p 4210:4210/udp -e DISPLAY=host.docker.internal:0.0 pybullet-aco-twin
```

#### Opción B: Usando Entorno Local
```bash
python digital_twin.py
```

Al iniciarse, el gemelo digital se suscribirá al puerto UDP 4210 y comenzará a renderizar la exploración y posterior convergencia del enjambre según los datos enviados por los ESP32.

---

## 8. 📹 Demostración en Video

En el siguiente enlace se encuentra el registro audiovisual de la práctica, evidenciando la interacción del hardware y la convergencia del algoritmo distribuido:

🎥 **[Ver Sustentación Práctica Real-to-Sim en YouTube](https://youtu.be/MkKA_Qkp9YE)** 
