import socket
import time
import pybullet as p
import pybullet_data

# Configurar servidor UDP para telemetría
UDP_IP = "0.0.0.0"
UDP_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

# Iniciar PyBullet
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

p.loadURDF("plane.urdf")

# Dimensiones del laberinto (5x5, escala 1 celda = 1 metro)
FILAS, COLS = 5, 5
mapa = [
    [0, 0, 1, 0, 0],
    [1, 0, 1, 0, 1],
    [0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 1, 0]
]

# Construir muros y meta
muro_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.45, 0.45, 0.3], rgbaColor=[0.4, 0.4, 0.4, 1])
muro_colision = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.45, 0.45, 0.3])

for r in range(FILAS):
    for c in range(COLS):
        if mapa[r][c] == 1:
            p.createMultiBody(baseMass=0, baseCollisionShapeIndex=muro_colision,
                              baseVisualShapeIndex=muro_visual, basePosition=[r, c, 0.3])

# Marcador de meta
meta_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.05], rgbaColor=[0, 1, 0, 0.6])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=meta_visual, basePosition=[4, 4, 0.05])

# Crear 3 carritos virtuales representados con colores distintos
colores = [[1, 0, 0, 1], [0, 0, 1, 1], [1, 1, 0, 1]]
robots = []
posiciones_actuales = [[0.0, 0.0, 0.15], [0.0, 0.0, 0.15], [0.0, 0.0, 0.15]]

for i in range(3):
    c_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.1], rgbaColor=colores[i])
    c_colision = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.1])
    bot = p.createMultiBody(baseMass=1.0, baseCollisionShapeIndex=c_colision,
                            baseVisualShapeIndex=c_visual, basePosition=[0, 0, 0.15 + i*0.02])
    robots.append(bot)

p.resetDebugVisualizerCamera(cameraDistance=6.5, cameraYaw=0, cameraPitch=-65, cameraTargetPosition=[2, 2, 0])

try:
    while True:
        # Lectura no bloqueante del socket UDP
        try:
            data, _ = sock.recvfrom(1024)
            msg = data.decode('utf-8').strip()
            partes = msg.split(',')

            if partes[0] == "POS" and len(partes) == 4:
                nodo_id = int(partes[1])
                target_x = float(partes[2])
                target_y = float(partes[3])

                if 0 <= nodo_id < 3:
                    posiciones_actuales[nodo_id][0] = target_x
                    posiciones_actuales[nodo_id][1] = target_y
        except BlockingIOError:
            pass

        # Interpolación y actualización de las posiciones en la simulación
        for i in range(3):
            p.resetBasePositionAndOrientation(
                robots[i],
                [posiciones_actuales[i][0], posiciones_actuales[i][1], 0.15],
                [0, 0, 0, 1]
            )

        p.stepSimulation()
        time.sleep(1.0 / 60.0)

finally:
    sock.close()
    p.disconnect()