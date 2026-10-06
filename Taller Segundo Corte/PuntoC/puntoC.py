import os
import sys
import time
import glob
import serial
import numpy as np
import pybullet as p
import pybullet_data

# ----------------------------------------------------
# 1. Ajustar Directorio de Trabajo a pybullet_robots
# ----------------------------------------------------
directorio_script = os.path.dirname(os.path.abspath(__file__))
ruta_robots = os.path.join(directorio_script, "pybullet_robots")

if not os.path.exists(ruta_robots):
    raise FileNotFoundError(f"No se encontró la carpeta: {ruta_robots}")

# Cambiar el directorio de trabajo para que PyBullet encuentre las mallas (.dae/.obj)
os.chdir(ruta_robots)

# Localizar automáticamente el archivo URDF de Atlas dentro del repositorio
coincidencias_atlas = glob.glob("**/atlas*.urdf", recursive=True)
if not coincidencias_atlas:
    raise FileNotFoundError("No se encontró ningún archivo URDF de Atlas en pybullet_robots.")

# Priorizar el modelo v4 con multisense si existe
ruta_atlas_relativa = next(
    (c for c in coincidencias_atlas if "multisense" in c.lower()),
    coincidencias_atlas[0]
)
print(f"Cargando modelo Atlas desde: {ruta_atlas_relativa}")

# ----------------------------------------------------
# 2. Conexión Serial con el ESP32
# ----------------------------------------------------
PUERTO_SERIAL = 'COM4'  # Ajusta al puerto COM de tu ESP32
BAUDRATE = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDRATE, timeout=0.01)
    print(f"ESP32 conectado en {PUERTO_SERIAL}")
except Exception as e:
    print(f"Aviso serial ({e}). Ejecutando en modo manual / sin hardware.")
    ser = None

# ----------------------------------------------------
# 3. Inicialización del Entorno PyBullet
# ----------------------------------------------------
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setAdditionalSearchPath(ruta_robots)

p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
p.setGravity(0, 0, -9.81)

# Cargar plano del suelo desde pybullet_data
p.loadURDF("plane.urdf", [0, 0, -3])

# Cargar cajas de soporte si están en el directorio
if os.path.exists("boston_box.urdf"):
    p.loadURDF("boston_box.urdf", [-2, 3, -2], useFixedBase=True)
    p.loadURDF("boston_box.urdf", [0, 3, -2], useFixedBase=True)

# Cargar Robot Atlas fijado a la base
atlas = p.loadURDF(ruta_atlas_relativa, [0, 3, -0.5], useFixedBase=True)

# ----------------------------------------------------
# 4. Mapeo de Articulaciones del Brazo
# ----------------------------------------------------
num_joints = p.getNumJoints(atlas)
arm_joints = []

for i in range(num_joints):
    info = p.getJointInfo(atlas, i)
    name = info[1].decode('utf-8').lower()
    # Identificar articulaciones rotacionales de brazos/hombros
    if any(k in name for k in ["arm", "sh", "el", "shoulder", "elbow"]) and info[2] in [p.JOINT_REVOLUTE, p.JOINT_PRISMATIC]:
        arm_joints.append(i)

# Seleccionar 3 articulaciones para controlar con los ejes del ESP32
controlled_joints = arm_joints[:3] if len(arm_joints) >= 3 else [3, 4, 5]
target_angles = [0.0, 0.0, 0.0]

# Posicionar cámara frente a Atlas
p.resetDebugVisualizerCamera(
    cameraDistance=2.0,
    cameraYaw=140,
    cameraPitch=-10,
    cameraTargetPosition=[0.0, 3.0, 0.3]
)

p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)

# ----------------------------------------------------
# 5. Bucle de Simulación y Control Fluido
# ----------------------------------------------------
try:
    while True:
        # Lectura serial continua
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                partes = line.split(',')
                if len(partes) >= 3:
                    dj1 = float(partes[0])
                    dj2 = float(partes[1])
                    dj3 = float(partes[2])

                    # Integración fluida con límites articulares
                    target_angles[0] = float(np.clip(target_angles[0] + dj1, -1.8, 1.8))
                    target_angles[1] = float(np.clip(target_angles[1] + dj2, -1.8, 1.8))
                    target_angles[2] = float(np.clip(target_angles[2] + dj3, -1.8, 1.8))
            except (ValueError, UnicodeDecodeError):
                pass

        # Aplicar el comando de posición a los actuadores
        for idx, j_id in enumerate(controlled_joints):
            p.setJointMotorControl2(
                atlas,
                j_id,
                p.POSITION_CONTROL,
                targetPosition=target_angles[idx],
                force=250
            )

        p.stepSimulation()
        time.sleep(1.0 / 60.0)

finally:
    p.disconnect()
    if ser:
        ser.close()