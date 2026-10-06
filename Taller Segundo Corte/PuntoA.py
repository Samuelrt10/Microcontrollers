import time
import numpy as np
import serial
from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary
from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
from gym_pybullet_drones.utils.enums import DroneModel, Physics

PUERTO_SERIAL = 'COM4'  # Ajusta tu puerto COM del ESP32
BAUDRATE = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDRATE, timeout=0.01)
    print(f"Conectado a ESP32 en {PUERTO_SERIAL}")
except Exception as e:
    print(f"Puerto serial no disponible ({e}). Usando waypoints por defecto.")
    ser = None

NUM_DRONES = 4
OFFSET_FORMACION = [
    np.array([0.3, 0.3, 0.0]),
    np.array([-0.3, 0.3, 0.0]),
    np.array([0.3, -0.3, 0.0]),
    np.array([-0.3, -0.3, 0.0])
]

initial_xyzs = np.array([
    [0.3, 0.3, 0.1],
    [-0.3, 0.3, 0.1],
    [0.3, -0.3, 0.1],
    [-0.3, -0.3, 0.1]
])

env = CtrlAviary(
    drone_model=DroneModel.CF2X,
    num_drones=NUM_DRONES,
    initial_xyzs=initial_xyzs,
    physics=Physics.PYB,
    gui=True
)

controllers = [DSLPIDControl(drone_model=DroneModel.CF2X) for _ in range(NUM_DRONES)]

target_pos = np.array([0.0, 0.0, 1.0])
action = np.zeros((NUM_DRONES, 4))

# CORRECCIÓN 1: Gymnasium retorna (obs, info)
obs, info = env.reset()

try:
    for i in range(20000):
        # 1. Lectura del ESP32
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                partes = line.split(',')
                if len(partes) == 3:
                    target_pos = np.array([float(partes[0]), float(partes[1]), float(partes[2])])
            except (ValueError, UnicodeDecodeError):
                pass

        # 2. Control de cada dron
        for j in range(NUM_DRONES):
            drone_target = target_pos + OFFSET_FORMACION[j]

            # obs[j] debe ser un array unidimensional de longitud 20 (estado del dron j)
            state_j = obs[j, :]

            action[j, :], _, _ = controllers[j].computeControlFromState(
                control_timestep=env.CTRL_TIMESTEP,
                state=state_j,
                target_pos=drone_target,
                target_rpy=np.zeros(3)
            )

        # CORRECCIÓN 2: step() retorna (obs, reward, terminated, truncated, info)
        obs, _, _, _, _ = env.step(action)
        env.render()
        time.sleep(env.CTRL_TIMESTEP)

finally:
    env.close()
    if ser:
        ser.close()