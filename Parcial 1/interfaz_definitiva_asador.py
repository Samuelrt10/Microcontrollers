import json
import time
import threading
import numpy as np
import requests
import sounddevice as sd
import speech_recognition as sr
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ==========================================================
# CONFIGURACIÓN GENERAL Y AUDIO
# ==========================================================
BAUD_RATE = 115200
SAMPLE_RATE = 16000
DURACION_REC = 4

ser = None
nivel_asador = 0
procesando = False

historial_chat = [
    {
        "role": "system",
        "content": (
            "Eres el asistente parrillero experto de un asador automatizado con LEDs térmicos (escala de 0 a 4).\n"
            "Niveles térmicos:\n"
            "- Nivel 0: Apagado / frío.\n"
            "- Nivel 1: Fuego bajo / mantener tibio / reposar carne / vegetales.\n"
            "- Nivel 2: Fuego medio / chorizos / pollo / cocción pareja.\n"
            "- Nivel 3: Fuego medio-alto / hamburguesas / cortes estándar.\n"
            "- Nivel 4: Fuego máximo / sellar carne gruesa (picanha, tomahawk) / potencia total.\n"
            "Tu tarea: Responder con amabilidad y dar consejos breves, seleccionando el nivel adecuado (0 al 4).\n"
            "Responde OBLIGATORIAMENTE en formato JSON con estas claves:\n"
            "{\n"
            '  "respuesta": "Texto corto de respuesta",\n'
            '  "nivel_sugerido": <número 0 a 4 o null>\n'
            "}"
        )
    }
]


# ==========================================================
# 1. INFERENCIA CON LLAMA 3.1:8B (ESCALA 0-4)
# ==========================================================
def consultar_llama_chat(mensaje_usuario):
    global historial_chat, nivel_asador
    url = "http://localhost:11434/api/chat"

    prompt_usuario = f"[Nivel actual: {nivel_asador}/4] Usuario: {mensaje_usuario}"
    historial_chat.append({"role": "user", "content": prompt_usuario})

    payload = {
        "model": "llama3.1:8b",
        "messages": historial_chat,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 90,
            "top_p": 0.9
        }
    }

    try:
        res = requests.post(url, json=payload, timeout=18)
        if res.status_code == 200:
            content = res.json()["message"]["content"]
            data = json.loads(content)
            historial_chat.append({"role": "assistant", "content": json.dumps(data)})
            return data
    except Exception:
        pass

    # Respaldo Heurístico si Ollama tarda
    f_low = mensaje_usuario.lower()
    if any(k in f_low for k in ["apag", "termin", "cero", "apág"]):
        return {"respuesta": "Entendido, apagando el asador.", "nivel_sugerido": 0}
    elif any(k in f_low for k in ["sellar", "picanh", "tomahawk", "bife", "full", "maxim", "candela"]):
        return {"respuesta": "Fuego al máximo en nivel 4 para sellado perfecto.", "nivel_sugerido": 4}
    elif any(k in f_low for k in ["hamburgues", "corte"]):
        return {"respuesta": "Fuego medio-alto en nivel 3.", "nivel_sugerido": 3}
    elif any(k in f_low for k in ["choriz", "morcill", "pollo", "medio"]):
        return {"respuesta": "Nivel 2 para cocción pareja sin quemar.", "nivel_sugerido": 2}
    elif any(k in f_low for k in ["sub", "aument", "mas", "calient"]):
        return {"respuesta": f"Subiendo a nivel {min(4, nivel_asador + 1)}.",
                "nivel_sugerido": min(4, nivel_asador + 1)}
    elif any(k in f_low for k in ["baj", "enfri", "men", "suav"]):
        return {"respuesta": f"Bajando a nivel {max(0, nivel_asador - 1)}.", "nivel_sugerido": max(0, nivel_asador - 1)}

    return {"respuesta": "Manteniendo el asador en el nivel actual.", "nivel_sugerido": nivel_asador}


# ==========================================================
# 2. CAPTURA Y RECONOCIMIENTO DE VOZ
# ==========================================================
def grabar_y_transcribir():
    try:
        audio_float = sd.rec(int(DURACION_REC * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()

        audio_int16 = (audio_float * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()

        recognizer = sr.Recognizer()
        audio_data = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)
        texto = recognizer.recognize_google(audio_data, language="es-CO")
        return texto
    except Exception:
        return ""


# ==========================================================
# 3. CONTROL SERIAL CON ESP32
# ==========================================================
def enviar_comando_esp(nivel):
    global ser
    if ser and ser.is_open:
        try:
            ser.write(f"{nivel}\n".encode('utf-8'))
        except Exception:
            pass


def conectar_serial():
    global ser
    puerto = combo_puertos.get()
    if not puerto:
        messagebox.showwarning("Atención", "Selecciona un puerto COM.")
        return

    if ser and ser.is_open:
        ser.close()
        btn_conectar.config(text="Conectar", bg="#4CAF50")
        lbl_estado.config(text="Desconectado", fg="#888888")
    else:
        try:
            ser = serial.Serial(puerto, BAUD_RATE, timeout=0.1)
            ser.dtr = False
            ser.rts = False
            btn_conectar.config(text="Desconectar", bg="#f44336")
            lbl_estado.config(text=f"Conectado a {puerto}", fg="#00E676")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def refrescar_puertos():
    puertos = [p.device for p in serial.tools.list_ports.comports()]
    combo_puertos['values'] = puertos
    if puertos:
        combo_puertos.current(0)


# ==========================================================
# 4. GESTIÓN DEL CHATBOX Y SINCRONIZACIÓN DE NIVELES
# ==========================================================
def agregar_mensaje(remitente, texto, tag):
    chat_box.config(state="normal")
    chat_box.insert(tk.END, f"{remitente}: ", tag)
    chat_box.insert(tk.END, f"{texto}\n\n")
    chat_box.see(tk.END)
    chat_box.config(state="disabled")


def procesar_mensaje(texto_usuario):
    global procesando, nivel_asador
    procesando = True
    btn_mic.config(state="disabled", text="⏳ Pensando...")
    btn_enviar.config(state="disabled")

    agregar_mensaje("Tú", texto_usuario, "tag_user")

    resultado = consultar_llama_chat(texto_usuario)
    respuesta = resultado.get("respuesta", "Entendido.")
    nuevo_nivel = resultado.get("nivel_sugerido")

    if nuevo_nivel is not None and isinstance(nuevo_nivel, int):
        nivel_asador = max(0, min(4, nuevo_nivel))
        enviar_comando_esp(nivel_asador)
        # Sincronizar el slider gráfico sin disparar eventos redundantes
        slider_calor.set(nivel_asador)
        lbl_nivel.config(text=f"Nivel Asador: {nivel_asador} / 4")

    agregar_mensaje("Llama 3.1", respuesta, "tag_ia")

    btn_mic.config(state="normal", text="🎤 Hablar por Micrófono")
    btn_enviar.config(state="normal")
    procesando = False


def hilo_voz():
    global procesando
    if procesando: return
    procesando = True
    btn_mic.config(state="disabled", text="🎙️ Escuchando...", bg="#f38ba8")

    def tarea():
        texto = grabar_y_transcribir()
        if texto:
            procesar_mensaje(texto)
        else:
            agregar_mensaje("Sistema", "No se detectó audio claro. Intenta de nuevo.", "tag_sys")
            btn_mic.config(state="normal", text="🎤 Hablar por Micrófono", bg="#e64553")
            global procesando
            procesando = False

    threading.Thread(target=tarea, daemon=True).start()


def evento_enviar_texto(event=None):
    texto = entry_texto.get().strip()
    if texto and not procesando:
        entry_texto.delete(0, tk.END)
        threading.Thread(target=procesar_mensaje, args=(texto,), daemon=True).start()


def evento_slider_movido(val):
    global nivel_asador
    nivel = int(float(val))
    if nivel != nivel_asador:
        nivel_asador = nivel
        lbl_nivel.config(text=f"Nivel Asador: {nivel_asador} / 4")
        enviar_comando_esp(nivel_asador)


# ==========================================================
# 5. INTERFAZ GRÁFICA TKINTER
# ==========================================================
root = tk.Tk()
root.title("Chatbot Parrillero IA (4 Niveles)")
root.geometry("490x690")
root.configure(bg="#181825")

style = ttk.Style()
style.theme_use('clam')

# Barra Superior: Conexión Serial
frame_top = tk.Frame(root, bg="#181825")
frame_top.pack(fill="x", padx=12, pady=6)

combo_puertos = ttk.Combobox(frame_top, width=12)
refrescar_puertos()
combo_puertos.pack(side="left", padx=4)

btn_refrescar = tk.Button(frame_top, text="🔄", bg="#313244", fg="white", command=refrescar_puertos)
btn_refrescar.pack(side="left", padx=2)

btn_conectar = tk.Button(frame_top, text="Conectar", bg="#4CAF50", fg="white", font=("Arial", 9, "bold"),
                         command=conectar_serial)
btn_conectar.pack(side="left", padx=4)

lbl_estado = tk.Label(frame_top, text="Desconectado", fg="#888888", bg="#181825")
lbl_estado.pack(side="left", padx=6)

# Barra de Control Térmico Manual (Deslizador)
frame_slider = tk.LabelFrame(root, text=" Control Manual de Calor (0 a 4) ", fg="#cdd6f4", bg="#1e1e2e", padx=10,
                             pady=6)
frame_slider.pack(fill="x", padx=12, pady=6)

lbl_nivel = tk.Label(frame_slider, text="Nivel Asador: 0 / 4", font=("Arial", 11, "bold"), fg="#fab387", bg="#1e1e2e")
lbl_nivel.pack(side="left", padx=6)

slider_calor = tk.Scale(
    frame_slider,
    from_=0,
    to=4,
    orient="horizontal",
    command=evento_slider_movido,
    bg="#1e1e2e",
    fg="white",
    highlightthickness=0,
    length=220,
    tickinterval=1
)
slider_calor.pack(side="right", padx=6)

# Ventana Principal del Chat
frame_chat = tk.LabelFrame(root, text=" Conversación con Llama 3.1 ", fg="#cdd6f4", bg="#1e1e2e", padx=8, pady=8)
frame_chat.pack(fill="both", expand=True, padx=12, pady=6)

chat_box = scrolledtext.ScrolledText(frame_chat, wrap=tk.WORD, bg="#11111b", fg="#cdd6f4", font=("Segoe UI", 10),
                                     state="disabled")
chat_box.pack(fill="both", expand=True)

chat_box.tag_config("tag_user", foreground="#89b4fa", font=("Segoe UI", 10, "bold"))
chat_box.tag_config("tag_ia", foreground="#a6e3a1", font=("Segoe UI", 10, "bold"))
chat_box.tag_config("tag_sys", foreground="#fab387", font=("Segoe UI", 9, "italic"))

# Entrada de Texto
frame_input = tk.Frame(root, bg="#181825")
frame_input.pack(fill="x", padx=12, pady=6)

entry_texto = tk.Entry(frame_input, font=("Segoe UI", 11), bg="#313244", fg="white", insertbackground="white")
entry_texto.pack(side="left", fill="x", expand=True, padx=4)
entry_texto.bind("<Return>", evento_enviar_texto)

btn_enviar = tk.Button(frame_input, text="Enviar", bg="#89b4fa", fg="#11111b", font=("Arial", 9, "bold"),
                       command=evento_enviar_texto)
btn_enviar.pack(side="left", padx=4)

# Botón Principal de Voz
btn_mic = tk.Button(root, text="🎤 Hablar por Micrófono", bg="#e64553", fg="white", font=("Arial", 12, "bold"), pady=8,
                    command=hilo_voz)
btn_mic.pack(fill="x", padx=12, pady=(0, 10))

agregar_mensaje("Llama 3.1",
                "¡Hola! Asador listo con 4 niveles térmicos. Puedes regular el calor hablando, escribiendo o deslizando la barra superior.",
                "tag_ia")

root.mainloop()