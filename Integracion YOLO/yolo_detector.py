import cv2
import time
from ultralytics import YOLO
import paho.mqtt.client as mqtt

# Configuracion MQTT (Mismo canal que Wokwi)
MQTT_BROKER = "broker.hivemq.com"
TOPIC = "lab_vision_carros_motos/control"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "yolo_pc_detector")
try:
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
    print("Conectado al Broker MQTT HiveMQ.")
except Exception as e:
    print(f"Error conectando a HiveMQ: {e}")
    exit()

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

ultimo_estado = ""
print("Deteccion iniciada. Presiona 'q' para salir.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.5, verbose=False)

    detectado_carro = False
    detectado_moto = False

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            nombre = model.names[cls_id]

            if nombre == 'car':
                detectado_carro = True
            elif nombre in ['motorcycle', 'motorbike']:
                detectado_moto = True

    if detectado_carro:
        estado_actual = "CAR"
    elif detectado_moto:
        estado_actual = "MOTO"
    else:
        estado_actual = "OFF"

    # Enviar solo cuando cambia para optimizar red
    if estado_actual != ultimo_estado:
        client.publish(TOPIC, estado_actual)
        print(f"Enviado a Wokwi -> {estado_actual}")
        ultimo_estado = estado_actual

    annotated = results[0].plot()
    cv2.imshow("Deteccion YOLO - Control Wokwi", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

client.publish(TOPIC, "OFF")
time.sleep(0.2)
cap.release()
cv2.destroyAllWindows()
client.loop_stop()
client.disconnect()
#hSs