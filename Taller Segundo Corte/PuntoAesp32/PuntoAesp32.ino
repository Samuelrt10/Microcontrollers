struct Waypoint {
  float x;
  float y;
  float z;
};

// Definición de puntos en el espacio de simulación
Waypoint puntoA = { 0.0,  0.0, 1.0};
Waypoint puntoB = { 1.5,  1.5, 1.5};
Waypoint puntoC = {-1.0,  1.0, 0.8};

int fase = 0;
unsigned long ultimoCambio = 0;
const unsigned long intervaloFase = 7000; // 7 segundos por posición

void setup() {
  Serial.begin(115200);
  delay(1000);
}

void loop() {
  unsigned long ahora = millis();

  // Transición cíclica: A -> B -> C
  if (ahora - ultimoCambio > intervaloFase) {
    ultimoCambio = ahora; // Corregido el operador de asignación
    fase = (fase + 1) % 3;
  }

  Waypoint objetivo;
  if (fase == 0) objetivo = puntoA;
  else if (fase == 1) objetivo = puntoB;
  else objetivo = puntoC;

  // Enviar "x,y,z" al simulador
  Serial.printf("%.2f,%.2f,%.2f\n", objetivo.x, objetivo.y, objetivo.z);

  delay(50); // 20 Hz de tasa de refresco
}