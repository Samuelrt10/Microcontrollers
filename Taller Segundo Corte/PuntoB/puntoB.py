import pybullet as p
import pybullet_data
import serial
import time
import numpy as np

# Configurar comunicación serial
PUERTO_SERIAL = 'COM3'  # Ajustar según tu puerto
BAUDRATE = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDRATE, timeout=0.01)
    print(f"ESP32 conectado en {PUERTO_SERIAL}")
except Exception as e:
    print(f"Aviso: Sin conexión serial ({e}). Se usarán valores nulos.")
    ser = None

# Inicializar PyBullet con GUI
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)
p.resetDebugVisualizerCamera(cameraDistance=2.0, cameraYaw=50, cameraPitch=-25, cameraTargetPosition=[0.6, 0, 0.4])

p.loadURDF("plane.urdf")

# Cargar mesa y objeto a manipular
mesa_id = p.loadURDF("table/table.urdf", [0.8, 0, -0.65], p.getQuaternionFromEuler([0, 0, 0]))
objeto_id = p.loadURDF("cube_small.urdf", [0.65, 0.2, 0.05])

# Cargar Baxter
baxter_id = p.loadURDF("baxter_common/baxter_description/urdf/baxter.urdf", [0, 0, 0], useFixedBase=True)

# Mapear articulaciones y efectores finales
num_joints = p.getNumJoints(baxter_id)
left_arm_joints = []
right_arm_joints = []
left_end_effector = -1
right_end_effector = -1
left_gripper_joints = []

for i in range(num_joints):
    info = p.getJointInfo(baxter_id, i)
    name = info[1].decode('utf-8')
    link_name = info[12].decode('utf-8')

    if "left" in name and info[2] in [p.JOINT_REVOLUTE, p.JOINT_PRISMATIC]:
        if "gripper" in name or "finger" in name:
            left_gripper_joints.append(i)
        else:
            left_arm_joints.append(i)

    if link_name == "left_gripper":
        left_end_effector = i
    elif link_name == "right_gripper":
        right_end_effector = i

# Si el nombre específico no coincide, usar los índices estándar de Baxter
if left_end_effector == -1:
    left_end_effector = 48  # Índice típico para el link del efector izquierdo

# Posición objetivo inicial del efector final
target_pos = np.array([0.6, 0.2, 0.2])
gripper_state = 0

try:
    while True:
        # 1. Leer comandos desde el ESP32
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                partes = line.split(',')
                if len(partes) == 5:
                    dx, dy, dz = float(partes[0]), float(partes[1]), float(partes[2])
                    gripper_state = int(partes[3])

                    # Actualizar setpoint cartesiano con límites seguros de trabajo
                    target_pos[0] = np.clip(target_pos[0] + dx, 0.3, 0.9)
                    target_pos[1] = np.clip(target_pos[1] + dy, -0.6, 0.6)
                    target_pos[2] = np.clip(target_pos[2] + dz, 0.0, 0.8)
            except (ValueError, UnicodeDecodeError):
                pass

        # 2. Cinemática inversa para el brazo izquierdo
        orientacion_fija = p.getQuaternionFromEuler([0, 1.57, 0])  # Pinza apuntando hacia abajo
        joint_poses = p.calculateInverseKinematics(
            baxter_id,
            left_end_effector,
            targetPosition=target_pos.tolist(),
            targetOrientation=orientacion_fija,
            maxNumIterations=20
        )

        # 3. Aplicar posiciones a las articulaciones del brazo
        for idx, j_idx in enumerate(left_arm_joints):
            if idx < len(joint_poses):
                p.setJointMotorControl2(
                    baxter_id,
                    j_idx,
                    p.POSITION_CONTROL,
                    targetPosition=joint_poses[idx],
                    force=100
                )

        # 4. Control de la pinza (0 = abierta, 1 = cerrada sobre el objeto)
        pos_dedos = 0.0 if gripper_state == 1 else 0.04
        for g_joint in left_gripper_joints:
            p.setJointMotorControl2(
                baxter_id,
                g_joint,
                p.POSITION_CONTROL,
                targetPosition=pos_dedos,
                force=40
            )

        p.stepSimulation()
        time.sleep(1.0 / 60.0)

finally:
    p.disconnect()
    if ser:
        ser.close()