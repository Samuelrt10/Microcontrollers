"""
Actividad 5: Control de Brazo Robótico en PyBullet mediante UART / ESP32
Universidad Militar Nueva Granada - Microcontroladores
Autor: Samuel Rubio Tamberg

Script en Python para PC (Host):
- Autodetección y conexión inmediata al puerto serie (UART) de la ESP32 a 115200 baudios.
- Recibe datos telemétricos del Joystick en tiempo real.
- Simulación física interactiva en PyBullet con el modelo 'brazo_robot.urdf'.
- Esquema de control conmutable e incremental:
    * MODO 0: Joystick controla Rotación de Base (joint_1) y Elevación de Hombro (joint_2).
    * MODO 1: Joystick controla Articulación de Codo (joint_3) y Apertura/Cierre de Pinza (dedo_izq/dedo_der).
- Interfaz gráfica en tiempo real con telemetría visual, límites articulares y modo de respaldo por teclado/GUI.
"""

import os
import sys
import time
import serial
import serial.tools.list_ports
import pybullet as p
import pybullet_data

# ==============================================================================
# 1. PARÁMETROS DE CONFIGURACIÓN Y CINEMÁTICA
# ==============================================================================
PUERTO_PREFERIDO = 'COM3'  # Se usará si está disponible, si no, se autodectará la ESP32
BAUD_RATE = 115200
URDF_FILENAME = "brazo_robot.urdf"

# Velocidades de incremento angular (radianes/segundo y metros/segundo)
VELOCIDAD_BASE = 0.035
VELOCIDAD_HOMBRO = 0.030
VELOCIDAD_CODO = 0.035
VELOCIDAD_PINZA = 0.001

# Límites de las articulaciones (según especificación del URDF)
LIMITES = {
    'joint_1': (-3.1416, 3.1416),
    'joint_2': (-2.0, 2.0),
    'joint_3': (-2.5, 2.5),
    'pinza': (-0.02, 0.03)  # Apertura/Cierre de pinza
}


# ==============================================================================
# 2. AUTODETECCIÓN Y CONEXIÓN INMEDIATA DEL PUERTO SERIAL
# ==============================================================================
def conectar_esp32_inmediato(puerto_sugerido=None, baudrate=115200):
    """
    Escanea y reconoce de inmediato el puerto serial de la ESP32
    sin necesidad de configurarlo manualmente si el puerto cambia.
    """
    puertos = list(serial.tools.list_ports.comports())
    if not puertos:
        print("[AVISO] No se detectó ningún dispositivo USB-Serial conectado actualmente.")
        return None

    puerto_destino = None

    # 1. Si el puerto sugerido existe en la lista activa, se conecta directo
    if puerto_sugerido:
        for p_info in puertos:
            if p_info.device.upper() == puerto_sugerido.upper():
                puerto_destino = p_info.device
                print(f"[SERIAL] Puerto preferido encontrado: {puerto_destino}")
                break

    # 2. Si no se encontró el sugerido, buscar chips típicos de la ESP32 (CP210x, CH340, FTDI, etc.)
    if not puerto_destino:
        palabras_clave = ['CP210', 'CH340', 'CH9102', 'FTDI', 'USB SERIAL', 'UART', 'ESP32']
        for p_info in puertos:
            cadena_info = f"{p_info.description} {p_info.manufacturer or ''} {p_info.hwid}".upper()
            if any(kw in cadena_info for kw in palabras_clave):
                puerto_destino = p_info.device
                print(f"[AUTODETECT] ESP32 identificada en {puerto_destino}: {p_info.description}")
                break

    # 3. Si solo hay un único puerto disponible en Windows, tomarlo directamente
    if not puerto_destino and len(puertos) == 1:
        puerto_destino = puertos[0].device
        print(f"[AUTODETECT] Único puerto COM detectado: {puerto_destino} ({puertos[0].description})")

    # 4. Si hay varios y ninguno coincidió con el filtro, tomar el primero disponible
    if not puerto_destino and len(puertos) > 1:
        print("[INFO] Puertos seriales detectados en el sistema:")
        for idx, p_info in enumerate(puertos):
            print(f"  [{idx + 1}] {p_info.device} -> {p_info.description}")
        puerto_destino = puertos[0].device
        print(f"[AUTODETECT] Conectando al primer puerto disponible: {puerto_destino}")

    # Apertura del puerto
    if puerto_destino:
        try:
            conexion = serial.Serial(
                port=puerto_destino,
                baudrate=baudrate,
                timeout=0.05,
                dsrdtr=False,
                rtscts=False
            )
            conexion.reset_input_buffer()
            print(f"[OK] Conexión serial abierta exitosamente en {puerto_destino} a {baudrate} bps.\n")
            return conexion
        except Exception as e:
            print(f"[ERROR] No se pudo abrir {puerto_destino}: {e}")

    return None


esp32 = conectar_esp32_inmediato(PUERTO_PREFERIDO, BAUD_RATE)
if not esp32:
    print("[INFO] Iniciando PyBullet en modo de respaldo (controles por teclado y GUI).\n")

# ==============================================================================
# 3. INICIALIZACIÓN DEL ENTORNO PYBULLET
# ==============================================================================
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

# Configurar cámara para visualización óptima del brazo
p.resetDebugVisualizerCamera(
    cameraDistance=1.6,
    cameraYaw=45,
    cameraPitch=-25,
    cameraTargetPosition=[0, 0, 0.4]
)

# Cargar plano de suelo y modelo del robot
p.loadURDF("plane.urdf")

directorio_actual = os.path.dirname(os.path.abspath(__file__))
ruta_urdf = os.path.join(directorio_actual, URDF_FILENAME)

if not os.path.exists(ruta_urdf):
    sys.exit(f"[ERROR] Archivo URDF no encontrado en: {ruta_urdf}")

robot_id = p.loadURDF(ruta_urdf, [0, 0, 0], useFixedBase=True)

# Mapear articulaciones por nombre
num_joints = p.getNumJoints(robot_id)
joint_map = {}
for i in range(num_joints):
    info = p.getJointInfo(robot_id, i)
    nombre = info[1].decode('utf-8')
    joint_map[nombre] = i

print("[INFO] Articulaciones detectadas:", list(joint_map.keys()))

# Índices requeridos
idx_j1 = joint_map.get('joint_1', 0)
idx_j2 = joint_map.get('joint_2', 1)
idx_j3 = joint_map.get('joint_3', 2)
idx_d_izq = joint_map.get('dedo_izq', 3)
idx_d_der = joint_map.get('dedo_der', 4)

# Posiciones angulares iniciales
pos_j1 = 0.0
pos_j2 = 0.2
pos_j3 = 0.3
pos_pinza = 0.01  # Ligeramente abierta

# Aplicar posiciones iniciales
p.resetJointState(robot_id, idx_j1, pos_j1)
p.resetJointState(robot_id, idx_j2, pos_j2)
p.resetJointState(robot_id, idx_j3, pos_j3)
p.resetJointState(robot_id, idx_d_izq, pos_pinza)
p.resetJointState(robot_id, idx_d_der, pos_pinza)

# Modo activo por defecto (0: Base/Hombro, 1: Codo/Pinza)
modo_activo = 0

# Identificador de texto en pantalla para telemetría
debug_text_id = -1


def limitar(valor, limites):
    return max(limites[0], min(valor, limites[1]))


def actualizar_motores():
    """Envía los comandos de control de posición a todas las articulaciones."""
    p.setJointMotorControl2(robot_id, idx_j1, p.POSITION_CONTROL, targetPosition=pos_j1, force=200)
    p.setJointMotorControl2(robot_id, idx_j2, p.POSITION_CONTROL, targetPosition=pos_j2, force=200)
    p.setJointMotorControl2(robot_id, idx_j3, p.POSITION_CONTROL, targetPosition=pos_j3, force=150)
    p.setJointMotorControl2(robot_id, idx_d_izq, p.POSITION_CONTROL, targetPosition=pos_pinza, force=60)
    p.setJointMotorControl2(robot_id, idx_d_der, p.POSITION_CONTROL, targetPosition=pos_pinza, force=60)


# ==============================================================================
# 4. BUCLE DE CONTROL EN TIEMPO REAL
# ==============================================================================
print("\n" + "=" * 60)
print("SISTEMA DE TELEOPERACIÓN ACTIVO")
print("MODO 0: Eje X -> Base (joint_1), Eje Y -> Hombro (joint_2)")
print("MODO 1: Eje Y -> Codo (joint_3), Eje X -> Pinza (dedo_izq/der)")
print("Pulsador SW: Conmuta entre MODO 0 y MODO 1")
print("Teclas de respaldo: [1] Modo 0, [2] Modo 1, [Espacio] Toggle Pinza")
print("=" * 60 + "\n")

try:
    while p.isConnected():
        norm_x = 0.0
        norm_y = 0.0
        sw_presionado = 0

        # --- A. LECTURA SERIAL DESDE LA ESP32 ---
        if esp32 and esp32.is_open:
            try:
                # Leer las últimas tramas disponibles para sincronización en tiempo real
                while esp32.in_waiting > 0:
                    linea = esp32.readline().decode('utf-8', errors='ignore').strip()
                    if linea:
                        partes = linea.split(',')
                        if len(partes) >= 4:
                            norm_x = float(partes[0])
                            norm_y = float(partes[1])
                            sw_presionado = int(partes[2])
                            modo_activo = int(partes[3])
            except Exception as ex:
                pass

        # --- B. LECTURA DE TECLADO (RESPALDO / MANUAL) ---
        keys = p.getKeyboardEvents()
        if ord('1') in keys and keys[ord('1')] & p.KEY_WAS_TRIGGERED:
            modo_activo = 0
        if ord('2') in keys and keys[ord('2')] & p.KEY_WAS_TRIGGERED:
            modo_activo = 1
        if ord(' ') in keys and keys[ord(' ')] & p.KEY_WAS_TRIGGERED:
            pos_pinza = LIMITES['pinza'][0] if pos_pinza > 0 else LIMITES['pinza'][1]

        # Flechas de teclado como respaldo si no hay señal del joystick
        if norm_x == 0.0 and norm_y == 0.0:
            if p.B3G_LEFT_ARROW in keys and keys[p.B3G_LEFT_ARROW] & p.KEY_IS_DOWN:
                norm_x = -1.0
            elif p.B3G_RIGHT_ARROW in keys and keys[p.B3G_RIGHT_ARROW] & p.KEY_IS_DOWN:
                norm_x = 1.0
            if p.B3G_UP_ARROW in keys and keys[p.B3G_UP_ARROW] & p.KEY_IS_DOWN:
                norm_y = 1.0
            elif p.B3G_DOWN_ARROW in keys and keys[p.B3G_DOWN_ARROW] & p.KEY_IS_DOWN:
                norm_y = -1.0

        # --- C. INTEGRACIÓN INCREMENTAL SEGÚN EL MODO CONMUTABLE ---
        if modo_activo == 0:
            # Control de Base (X) y Hombro (Y)
            pos_j1 += norm_x * VELOCIDAD_BASE
            pos_j2 += norm_y * VELOCIDAD_HOMBRO
            pos_j1 = limitar(pos_j1, LIMITES['joint_1'])
            pos_j2 = limitar(pos_j2, LIMITES['joint_2'])
            desc_modo = "MODO 0: Base / Hombro"
        else:
            # Control de Codo (Y) y Pinza (X)
            pos_j3 += norm_y * VELOCIDAD_CODO
            pos_pinza += norm_x * VELOCIDAD_PINZA
            pos_j3 = limitar(pos_j3, LIMITES['joint_3'])
            pos_pinza = limitar(pos_pinza, LIMITES['pinza'])
            desc_modo = "MODO 1: Codo / Pinza"

        # Actualizar la cinemática de los actuadores
        actualizar_motores()

        # --- D. TELEMETRÍA EN PANTALLA ---
        puerto_str = esp32.port if (esp32 and esp32.is_open) else "DESCONECTADO (Modo Teclado)"
        texto_telemetria = (
            f"=== TELEOPERACIÓN ESP32 ({puerto_str}) ===\n"
            f"Modo: {desc_modo}\n"
            f"Joystick X: {norm_x:+.2f} | Y: {norm_y:+.2f}\n"
            f"Base (j1): {pos_j1:+.2f} rad\n"
            f"Hombro (j2): {pos_j2:+.2f} rad\n"
            f"Codo (j3): {pos_j3:+.2f} rad\n"
            f"Pinza: {pos_pinza * 1000:+.1f} mm\n"
            f"Presione SW / '1' / '2' para alternar modo"
        )

        debug_text_id = p.addUserDebugText(
            text=texto_telemetria,
            textPosition=[-0.8, -0.8, 0.8],
            textColorRGB=[1, 1, 0] if modo_activo == 0 else [0, 1, 1],
            textSize=1.1,
            replaceItemUniqueId=debug_text_id
        )

        p.stepSimulation()
        time.sleep(1 / 100)

except KeyboardInterrupt:
    print("\n[INFO] Simulación finalizada por el usuario.")
finally:
    if esp32 and esp32.is_open:
        esp32.close()
        print("[INFO] Conexión serial cerrada.")
    p.disconnect()
