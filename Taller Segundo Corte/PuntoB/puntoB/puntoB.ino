// Pines de entrada en el ESP32
const int PIN_JOY_X = 34;      // Eje X
const int PIN_JOY_Y = 35;      // Eje Y
const int PIN_JOY_Z = 32;      // Eje Z (o botón arriba/abajo)
const int PIN_GRIPPER = 25;    // Pulsador de agarre
const int PIN_CAMBIO_BRAZO = 26; // Alternar brazo izquierdo (0) / derecho (1)

int estadoGripper = 0;
int brazoActivo = 0; // 0: Izquierdo, 1: Derecho

// Zona muerta para evitar drift del joystick
const int CENTRO_ADC = 2048;
const int ZONA_MUERTA = 250;

float normalizarEje(int valorRaw) {
  int diff = valorRaw - CENTRO_ADC;
  if (abs(diff) < ZONA_MUERTA) return 0.0f;
  return (float)diff / 2048.0f; // Rango de -1.0 a 1.0
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_GRIPPER, INPUT_PULLUP);
  pinMode(PIN_CAMBIO_BRAZO, INPUT_PULLUP);
}

void loop() {
  // Lectura analógica (12 bits: 0 a 4095)
  float dx = normalizarEje(analogRead(PIN_JOY_X));
  float dy = normalizarEje(analogRead(PIN_JOY_Y));
  float dz = normalizarEje(analogRead(PIN_JOY_Z));

  // Lectura de botones con antirrebote simple
  if (digitalRead(PIN_GRIPPER) == LOW) {
    estadoGripper = !estadoGripper;
    delay(250);
  }
  if (digitalRead(PIN_CAMBIO_BRAZO) == LOW) {
    brazoActivo = !brazoActivo;
    delay(250);
  }

  // Enviar: dx, dy, dz, estado_pinza, brazo
  // Multiplicador de escala de velocidad (ej. paso máx 0.01 m por frame)
  Serial.printf("%.3f,%.3f,%.3f,%d,%d\n", dx * 0.01f, dy * 0.01f, dz * 0.01f, estadoGripper, brazoActivo);

  delay(20); // Refresco a 50 Hz
}