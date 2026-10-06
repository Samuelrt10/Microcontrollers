// Pines analógicos en el ESP32
const int PIN_EJE_1 = 34; // Hombro / Brazo (Pitch)
const int PIN_EJE_2 = 35; // Hombro / Brazo (Roll)
const int PIN_EJE_3 = 32; // Codo / Giro (Yaw)

const int CENTRO_ADC = 2048;
const int ZONA_MUERTA = 250;

float leerDelta(int pin) {
  int raw = analogRead(pin);
  int diff = raw - CENTRO_ADC;
  if (abs(diff) < ZONA_MUERTA) return 0.0f;
  return ((float)diff / 2048.0f) * 0.02f; // Incremento angular suave (rad/ciclo)
}

void setup() {
  Serial.begin(115200);
}

void loop() {
  float dj1 = leerDelta(PIN_EJE_1);
  float dj2 = leerDelta(PIN_EJE_2);
  float dj3 = leerDelta(PIN_EJE_3);

  // Enviar incrementos: d_articulacion1, d_articulacion2, d_articulacion3
  Serial.printf("%.4f,%.4f,%.4f\n", dj1, dj2, dj3);

  delay(20); // 50 Hz
}
