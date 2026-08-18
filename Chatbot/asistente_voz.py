import json
import time
import numpy as np
import paho.mqtt.client as mqtt
import requests
import sounddevice as sd
import speech_recognition as sr

# ================= Configuración Ollama Local =================
OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO_LOCAL = "llama3.1:8b"

SYSTEM_PROMPT = """
Eres el controlador domótico de un LED conectado a un ESP32.
Tu único trabajo es interpretar la intención del usuario y responder ESTRICTAMENTE con un objeto JSON válido con este formato:
{
  "comando": "LED_ON" | "LED_OFF" | "NINGUNO",
  "respuesta": "Frase breve confirmando la acción"
}

Reglas:
- Si el usuario pide encender, iluminar o que está oscuro -> comando: "LED_ON"
- Si el usuario pide apagar, oscurecer o dormir -> comando: "LED_OFF"
- Si no tiene relación con luces -> comando: "NINGUNO"
"""

# ================= Configuración MQTT =================
MQTT_BROKER = "broker.hivemq.com"
TOPIC_CONTROL = "lab_micro_deepseek/led_unico"

client_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "pc_voice_llama31")
try:
    client_mqtt.connect(MQTT_BROKER, 1883, 60)
    client_mqtt.loop_start()
    print("Conectado al Broker MQTT.")
except Exception as e:
    print(f"Error conectando a MQTT: {e}")


# ================= Inferencia con Llama 3.1:8b =================
def consultar_llama(texto_usuario):
    payload = {
        "model": MODELO_LOCAL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": texto_usuario},
        ],
        "format": "json",  # Fuerza a Llama a generar JSON estructurado garantizado
        "stream": False,
        "options": {"temperature": 0.1},
    }

    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=12)
        res.raise_for_status()
        raw_json = res.json()["message"]["content"]
        return json.loads(raw_json)
    except Exception as e:
        print(f"Error consultando Llama 3.1: {e}")
        return {"comando": "NINGUNO", "respuesta": "Error procesando orden."}


# ================= Captura de Voz con Sounddevice =================
def grabar_voz(duracion=4, sample_rate=16000):
    print("\n>> ESCUCHANDO... Habla ahora:")
    try:
        audio = sd.rec(
            int(duracion * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()

        recognizer = sr.Recognizer()
        audio_source = sr.AudioData(audio.tobytes(), sample_rate, 2)
        texto = recognizer.recognize_google(audio_source, language="es-ES")
        print(f"Tú dijiste: '{texto}'")
        return texto
    except sr.UnknownValueError:
        print("No se logró entender el audio.")
        return None
    except Exception as e:
        print(f"Error en captura: {e}")
        return None


# ================= Bucle Principal =================
def main():
    print(f"=== ASISTENTE DE VOZ CON {MODELO_LOCAL.upper()} LOCAL ===")
    print("Presiona [ENTER] para hablar. Di 'salir' para terminar.\n")

    while True:
        input("Presiona [ENTER] para hablar...")
        frase = grabar_voz()

        if frase:
            if "salir" in frase.lower() or "terminar" in frase.lower():
                print("Hasta luego!")
                break

            print("Pensando con Llama 3.1...")
            resultado = consultar_llama(frase)
            comando = resultado.get("comando", "NINGUNO")
            respuesta = resultado.get("respuesta", "")

            print(f"Llama 3.1: {respuesta} | [Comando: {comando}]")

            if comando in ["LED_ON", "LED_OFF"]:
                client_mqtt.publish(TOPIC_CONTROL, comando)
                print(f"-> Publicado a Wokwi: {comando}")


if __name__ == "__main__":
    main()

#LLAMA SE CORRE EN LOCAL, ABRIR OLLAMA POR SI ACASO

