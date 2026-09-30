import os
import sys
import time
import threading
import queue
import cv2
import numpy as np
import pybullet as p
import pybullet_data
import serial
import serial.tools.list_ports

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_URDF = os.path.join(BASE_DIR, "brazo_robot.urdf")
CARPETA_IMAGENES = os.path.join(BASE_DIR, "imagenes")

MAPA_ARCHIVOS = {
    '*': 'asterisco',
    '#': 'numeral'
}

X_CENTRO = 0.35
Y_CENTRO = 0.00
Z_MESA = 0.40
Z_AIRE = 0.46
TAMANO_DIBUJO = 0.12

TRAZOS_CANONICOS = {
    '0': [
        [(0.50 + 0.28 * np.sin(a), 0.50 + 0.40 * np.cos(a)) for a in np.linspace(0, 2 * np.pi, 36)]
    ],
    '1': [
        [(0.35, 0.75), (0.50, 0.92), (0.50, 0.08)],
        [(0.30, 0.08), (0.70, 0.08)]
    ],
    '2': [
        [(0.25, 0.72)] +
        [(0.50 + 0.25 * np.cos(a), 0.70 + 0.22 * np.sin(a)) for a in np.linspace(np.pi, 0, 18)] +
        [(0.25, 0.08), (0.75, 0.08)]
    ],
    '3': [
        [(0.28, 0.85)] +
        [(0.50 + 0.25 * np.cos(a), 0.72 + 0.20 * np.sin(a)) for a in np.linspace(np.pi * 0.7, -np.pi * 0.3, 15)] +
        [(0.45, 0.50)] +
        [(0.50 + 0.26 * np.cos(a), 0.28 + 0.22 * np.sin(a)) for a in np.linspace(np.pi * 0.3, -np.pi * 0.8, 15)] +
        [(0.26, 0.15)]
    ],
    '4': [
        [(0.70, 0.92), (0.25, 0.35), (0.78, 0.35)],
        [(0.70, 0.92), (0.70, 0.08)]
    ],
    '5': [
        [(0.72, 0.92), (0.28, 0.92), (0.28, 0.55)] +
        [(0.50 + 0.25 * np.cos(a), 0.32 + 0.23 * np.sin(a)) for a in np.linspace(np.pi * 0.6, -np.pi * 0.8, 18)] +
        [(0.30, 0.10)]
    ],
    '6': [
        [(0.68, 0.85), (0.40, 0.65), (0.26, 0.38)] +
        [(0.50 + 0.24 * np.cos(a), 0.30 + 0.22 * np.sin(a)) for a in np.linspace(-np.pi, np.pi, 24)]
    ],
    '7': [
        [(0.25, 0.92), (0.75, 0.92), (0.42, 0.08)],
        [(0.35, 0.52), (0.62, 0.52)]
    ],
    '8': [
        [(0.50 + 0.22 * np.cos(a), 0.70 + 0.21 * np.sin(a)) for a in np.linspace(-np.pi / 2, 3 * np.pi / 2, 20)] +
        [(0.50 + 0.25 * np.cos(a), 0.28 + 0.22 * np.sin(a)) for a in np.linspace(np.pi / 2, -3 * np.pi / 2, 24)]
    ],
    '9': [
        [(0.50 + 0.24 * np.cos(a), 0.70 + 0.22 * np.sin(a)) for a in np.linspace(np.pi, -np.pi, 24)] +
        [(0.74, 0.70), (0.70, 0.35), (0.35, 0.08)]
    ],
    'A': [
        [(0.24, 0.08), (0.50, 0.92), (0.76, 0.08)],
        [(0.34, 0.40), (0.66, 0.40)]
    ],
    'B': [
        [(0.28, 0.08), (0.28, 0.92)],
        [(0.28, 0.92)] + [(0.42 + 0.22 * np.cos(a), 0.71 + 0.21 * np.sin(a)) for a in np.linspace(np.pi / 2, -np.pi / 2, 12)] + [(0.28, 0.50)],
        [(0.28, 0.50)] + [(0.44 + 0.24 * np.cos(a), 0.29 + 0.21 * np.sin(a)) for a in np.linspace(np.pi / 2, -np.pi / 2, 14)] + [(0.28, 0.08)]
    ],
    'C': [
        [(0.50 + 0.28 * np.cos(a), 0.50 + 0.40 * np.sin(a)) for a in np.linspace(np.pi * 0.25, np.pi * 1.75, 24)]
    ],
    'D': [
        [(0.28, 0.08), (0.28, 0.92)],
        [(0.28, 0.92)] + [(0.35 + 0.35 * np.cos(a), 0.50 + 0.42 * np.sin(a)) for a in np.linspace(np.pi / 2, -np.pi / 2, 18)] + [(0.28, 0.08)]
    ],
    '*': [
        [(0.50, 0.15), (0.50, 0.85)],
        [(0.22, 0.32), (0.78, 0.68)],
        [(0.22, 0.68), (0.78, 0.32)]
    ],
    '#': [
        [(0.38, 0.12), (0.38, 0.88)],
        [(0.62, 0.12), (0.62, 0.88)],
        [(0.18, 0.62), (0.82, 0.62)],
        [(0.18, 0.38), (0.82, 0.38)]
    ]
}

def asegurar_imagenes():
    os.makedirs(CARPETA_IMAGENES, exist_ok=True)
    w, h = 300, 300
    for tecla, trazos in TRAZOS_CANONICOS.items():
        nombre = MAPA_ARCHIVOS.get(tecla, tecla) + ".png"
        ruta = os.path.join(CARPETA_IMAGENES, nombre)
        if not os.path.exists(ruta):
            img = np.zeros((h, w), dtype=np.uint8)
            for stroke in trazos:
                pts = np.array([
                    [int(p_elem[0] * (w - 40) + 20), int((1.0 - p_elem[1]) * (h - 40) + 20)]
                    for p_elem in stroke
                ], dtype=np.int32)
                cv2.polylines(img, [pts], isClosed=False, color=255, thickness=6, lineType=cv2.LINE_AA)
            cv2.imwrite(ruta, img)
            print(f"[IMAGEN] Plantilla generada: {nombre}")

def obtener_trazos_3d(tecla):
    tecla_upper = tecla.upper()
    nombre_archivo = MAPA_ARCHIVOS.get(tecla_upper, tecla_upper) + ".png"
    ruta_img = os.path.join(CARPETA_IMAGENES, nombre_archivo)

    if os.path.exists(ruta_img):
        img = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
            pixeles_blancos = cv2.countNonZero(thresh)
            if pixeles_blancos == 0:
                print(f"[AVISO] La imagen {nombre_archivo} parece estar vacia.")

    if tecla_upper not in TRAZOS_CANONICOS:
        print(f"[ERROR] Caracter '{tecla}' no esta en el catalogo de teclas (0-9, A-D, *, #)")
        return []

    trazos_can = TRAZOS_CANONICOS[tecla_upper]
    trazos_3d = []

    for stroke in trazos_can:
        puntos_trazo = []
        for (u, v) in stroke:
            y_robot = Y_CENTRO + (u - 0.5) * TAMANO_DIBUJO
            x_robot = X_CENTRO + (v - 0.5) * TAMANO_DIBUJO
            puntos_trazo.append([x_robot, y_robot, Z_MESA])
        trazos_3d.append(puntos_trazo)

    return trazos_3d

def resolver_ik(x, y, z, L1=0.40, L2=0.15, z_hombro=0.60):
    th1 = np.arctan2(y, x)
    r = np.sqrt(x**2 + y**2)
    z_rel = z - z_hombro

    d2 = r**2 + z_rel**2
    d = np.sqrt(d2)

    min_reach = abs(L1 - L2) + 1e-4
    max_reach = (L1 + L2) - 1e-4
    d_clamped = np.clip(d, min_reach, max_reach)
    if d != d_clamped:
        ratio = d_clamped / d
        r *= ratio
        z_rel *= ratio
        d2 = r**2 + z_rel**2

    cos_q3 = (d2 - L1**2 - L2**2) / (2.0 * L1 * L2)
    cos_q3 = np.clip(cos_q3, -1.0, 1.0)
    sin_q3 = np.sqrt(1.0 - cos_q3**2)
    th3 = np.arctan2(sin_q3, cos_q3)

    phi = np.arctan2(r, z_rel)
    psi = np.arctan2(L2 * sin_q3, L1 + L2 * cos_q3)
    th2 = phi - psi

    return float(th1), float(th2), float(th3)

def mover_efector(robot_id, x, y, z, pasos=10, sleep_time=0.004):
    th1, th2, th3 = resolver_ik(x, y, z)
    p.setJointMotorControl2(robot_id, 0, p.POSITION_CONTROL, targetPosition=th1, force=250)
    p.setJointMotorControl2(robot_id, 1, p.POSITION_CONTROL, targetPosition=th2, force=250)
    p.setJointMotorControl2(robot_id, 2, p.POSITION_CONTROL, targetPosition=th3, force=250)
    for _ in range(pasos):
        p.stepSimulation()
        time.sleep(sleep_time)

def obtener_pos_punta(robot_id):
    link2_state = p.getLinkState(robot_id, 2)
    pos_l2, orn_l2 = link2_state[4], link2_state[5]
    punta_pos, _ = p.multiplyTransforms(pos_l2, orn_l2, [0, 0, 0.15], [0, 0, 0, 1])
    return punta_pos

def dibujar_tecla(robot_id, tecla):
    trazos = obtener_trazos_3d(tecla)
    if not trazos:
        return

    p.removeAllUserDebugItems()
    p.addUserDebugText(
        f"Tecla: '{tecla}'",
        [X_CENTRO, 0.0, 0.62],
        textColorRGB=[0.1, 0.2, 0.9],
        textSize=1.6,
        lifeTime=0
    )

    print(f"\n>>> [DIBUJO] Trazando tecla '{tecla}' ({len(trazos)} trazos)...")

    for idx_trazo, stroke in enumerate(trazos, start=1):
        if not stroke:
            continue

        p_inicio = stroke[0]
        mover_efector(robot_id, p_inicio[0], p_inicio[1], Z_AIRE, pasos=15)
        mover_efector(robot_id, p_inicio[0], p_inicio[1], Z_MESA, pasos=10)
        punto_previo = obtener_pos_punta(robot_id)

        for p_sig in stroke[1:]:
            dist = np.linalg.norm(np.array(p_sig) - np.array(punto_previo))
            subpasos = max(4, int(dist / 0.005))

            for paso in range(1, subpasos + 1):
                interp_x = punto_previo[0] + (p_sig[0] - punto_previo[0]) * (paso / subpasos)
                interp_y = punto_previo[1] + (p_sig[1] - punto_previo[1]) * (paso / subpasos)
                interp_z = Z_MESA

                mover_efector(robot_id, interp_x, interp_y, interp_z, pasos=2, sleep_time=0.002)
                punto_actual = obtener_pos_punta(robot_id)

                p.addUserDebugLine(
                    punto_previo,
                    punto_actual,
                    lineColorRGB=[1.0, 0.0, 0.0],
                    lineWidth=4,
                    lifeTime=0
                )
                punto_previo = punto_actual

        mover_efector(robot_id, punto_previo[0], punto_previo[1], Z_AIRE, pasos=10)

    mover_efector(robot_id, 0.28, 0.0, 0.55, pasos=20)
    print(f">>> [DIBUJO] Tecla '{tecla}' completada exitosamente!\n")

cola_consola = queue.Queue()

def lector_consola():
    while True:
        try:
            linea = sys.stdin.readline()
            if not linea:
                break
            txt = linea.strip()
            if txt:
                cola_consola.put(txt)
        except Exception:
            break

def main():
    asegurar_imagenes()

    if not os.path.exists(RUTA_URDF):
        print(f"[ERROR CRITICO] Archivo URDF no encontrado en: {RUTA_URDF}")
        return

    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)

    p.resetDebugVisualizerCamera(
        cameraDistance=1.1,
        cameraYaw=55,
        cameraPitch=-32,
        cameraTargetPosition=[0.35, 0.0, 0.40]
    )

    p.loadURDF("plane.urdf")

    mesa_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.14, 0.14, 0.19])
    mesa_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.14, 0.14, 0.19], rgbaColor=[0.25, 0.25, 0.28, 1.0])
    p.createMultiBody(0, mesa_col, mesa_vis, basePosition=[X_CENTRO, Y_CENTRO, 0.19])

    papel_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.10, 0.10, 0.002], rgbaColor=[0.96, 0.96, 0.96, 1.0])
    p.createMultiBody(0, -1, papel_vis, basePosition=[X_CENTRO, Y_CENTRO, 0.382])

    robot_id = p.loadURDF(RUTA_URDF, [0, 0, 0], useFixedBase=True)
    mover_efector(robot_id, 0.28, 0.0, 0.55, pasos=30)

    PUERTO = 'COM3'
    ser = None
    try:
        puertos_disp = [p_info.device for p_info in serial.tools.list_ports.comports()]
        puerto_a_usar = PUERTO if PUERTO in puertos_disp else (puertos_disp[0] if puertos_disp else None)
        if puerto_a_usar:
            ser = serial.Serial(puerto_a_usar, 9600, timeout=0.05)
            print(f"[SERIAL] Conectado exitosamente en {puerto_a_usar}.")
        else:
            print("[SERIAL] No se detecto ESP32/Arduino por serial.")
    except Exception as e:
        print(f"[SERIAL] Aviso de conexion: {e}")
        ser = None

    t_consola = threading.Thread(target=lector_consola, daemon=True)
    t_consola.start()

    print("\n" + "=" * 65)
    print("SISTEMA DE DIBUJO ROBOTICO ACTIVADO")
    print("Opciones para ingresar teclas:")
    print("  1. Teclado fisico 4x4 conectado a la ESP32 (COM3 / Serial)")
    print("  2. Teclado de tu computadora en la ventana de PyBullet (0-9, A-D, *, #)")
    print("  3. Escribir la tecla en esta consola y presionar Enter")
    print("  4. Escribe 'q' para salir")
    print("=" * 65 + "\n")

    MAPA_TECLAS_PYBULLET = {
        ord('0'): '0', ord('1'): '1', ord('2'): '2', ord('3'): '3',
        ord('4'): '4', ord('5'): '5', ord('6'): '6', ord('7'): '7',
        ord('8'): '8', ord('9'): '9',
        ord('a'): 'A', ord('b'): 'B', ord('c'): 'C', ord('d'): 'D',
        ord('A'): 'A', ord('B'): 'B', ord('C'): 'C', ord('D'): 'D',
        ord('*'): '*', ord('#'): '#'
    }

    try:
        while True:
            p.stepSimulation()
            tecla_detectada = None

            if ser and ser.is_open:
                try:
                    if ser.in_waiting > 0:
                        linea = ser.readline().decode('utf-8', errors='ignore').strip()
                        if linea:
                            tecla_detectada = linea[0].upper()
                except Exception:
                    ser = None

            if tecla_detectada is None:
                keys = p.getKeyboardEvents()
                for k, v in keys.items():
                    if v & p.KEY_WAS_TRIGGERED:
                        if k in MAPA_TECLAS_PYBULLET:
                            tecla_detectada = MAPA_TECLAS_PYBULLET[k]
                            break
                        elif k == 27 or k == ord('q') or k == ord('Q'):
                            return

            if tecla_detectada is None and not cola_consola.empty():
                cmd = cola_consola.get_nowait()
                if cmd.lower() == 'q':
                    break
                elif cmd:
                    tecla_detectada = cmd[0].upper()

            if tecla_detectada:
                print(f"[COMANDO] Tecla recibida: '{tecla_detectada}'")
                dibujar_tecla(robot_id, tecla_detectada)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[INFO] Ejecucion interrumpida.")
    finally:
        if ser and ser.is_open:
            ser.close()
        p.disconnect()
        print("[INFO] Simulacion cerrada correctamente.")

if __name__ == "__main__":
    main()
