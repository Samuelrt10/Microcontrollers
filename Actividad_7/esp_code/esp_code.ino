#include <WiFi.h>
#include <WiFiUdp.h>

// ASIGNACIÓN:
// 0: ESP32-S3 o Estándar (Actuará como AP)
// 1: ESP32 Estándar / S3 (Actuará como STA)
// 2: ESP32-S3 Super Mini (Actuará como STA)
#define NODO_ID 0  // <-- Cambiar a 1 o 2 según la placa correspondiente

const char *ssid = "ACO_SWARM_NET";
const char *password = "12345678";
const int UDP_PORT = 4210;

WiFiUDP udp;

// Laberinto 5x5: 0 = Camino libre, 1 = Muro
const int FILAS = 5;
const int COLS = 5;
const int mapa[FILAS][COLS] = {
  {0, 0, 1, 0, 0},
  {1, 0, 1, 0, 1},
  {0, 0, 0, 0, 0},
  {0, 1, 1, 1, 0},
  {0, 0, 0, 1, 0}
};

const int INICIO_X = 0, INICIO_Y = 0;
const int META_X = 4,   META_Y = 4;

float feromonas[FILAS][COLS];
const float EVAPORACION = 0.10f;
const float FEROMONA_BASE = 0.20f;

int posX = INICIO_X;
int posY = INICIO_Y;
int rutaX[50];
int rutaY[50];
int pasoRuta = 0;

void moverHormiga() {
  int dx[] = {0, 0, 1, -1};
  int dy[] = {1, -1, 0, 0};

  float pesos[4] = {0, 0, 0, 0};
  float sumaPesos = 0.0f;

  for (int k = 0; k < 4; k++) {
    int nx = posX + dx[k];
    int ny = posY + dy[k];

    if (nx >= 0 && nx < FILAS && ny >= 0 && ny < COLS && mapa[nx][ny] == 0) {
      float distMeta = abs(META_X - nx) + abs(META_Y - ny) + 1.0f;
      float eta = 1.0f / distMeta;
      float tau = feromonas[nx][ny];

      pesos[k] = tau * (eta * eta);
      sumaPesos += pesos[k];
    }
  }

  if (sumaPesos > 0) {
    float r = ((float)random(0, 10000) / 10000.0f) * sumaPesos;
    float acumulado = 0.0f;
    for (int k = 0; k < 4; k++) {
      acumulado += pesos[k];
      if (r <= acumulado && pesos[k] > 0) {
        posX += dx[k];
        posY += dy[k];
        break;
      }
    }
  }

  if (pasoRuta < 50) {
    rutaX[pasoRuta] = posX;
    rutaY[pasoRuta] = posY;
    pasoRuta++;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500); // Pausa de estabilización USB CDC para las S3

  // Inicializar feromonas
  for (int i = 0; i < FILAS; i++) {
    for (int j = 0; j < COLS; j++) {
      feromonas[i][j] = FEROMONA_BASE;
    }
  }

  // Configuración de red WiFi
  if (NODO_ID == 0) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(ssid, password);
    Serial.print("Nodo AP iniciado. IP: ");
    Serial.println(WiFi.softAPIP());
  } else {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Conectando a red ACO");
    while (WiFi.status() != WL_CONNECTED) {
      delay(250);
      Serial.print(".");
    }
    Serial.print("\nConectado con IP: ");
    Serial.println(WiFi.localIP());
  }

  udp.begin(UDP_PORT);
  // Generador de números aleatorios por hardware compatible con ESP32 / S3
  randomSeed(esp_random() + NODO_ID * 1000);
}

void loop() {
  // 1. Escuchar paquetes de feromona emitidos por los otros nodos
  int packetSize = udp.parsePacket();
  if (packetSize) {
    char buffer[64];
    int len = udp.read(buffer, sizeof(buffer) - 1);
    if (len > 0) buffer[len] = '\0';

    int fx, fy;
    float delta;
    if (sscanf(buffer, "FERO,%d,%d,%f", &fx, &fy, &delta) == 3) {
      if (fx >= 0 && fx < FILAS && fy >= 0 && fy < COLS) {
        feromonas[fx][fy] = (feromonas[fx][fy] * (1.0f - EVAPORACION)) + delta;
      }
    }
  }

  // 2. Dar un paso en el laberinto
  moverHormiga();

  IPAddress broadcastIP(192, 168, 4, 255);

  // 3. Si llega a la meta, difundir feromonas en la ruta recorrida
  if (posX == META_X && posY == META_Y) {
    float delta = 10.0f / (float)max(pasoRuta, 1);

    for (int p = 0; p < pasoRuta; p++) {
      char msg[64];
      snprintf(msg, sizeof(msg), "FERO,%d,%d,%.2f", rutaX[p], rutaY[p], delta);
      udp.beginPacket(broadcastIP, UDP_PORT);
      udp.write((const uint8_t *)msg, strlen(msg));
      udp.endPacket();
      feromonas[rutaX[p]][rutaY[p]] += delta;
      delay(2);
    }

    // Reiniciar al punto de partida para la siguiente iteración
    posX = INICIO_X;
    posY = INICIO_Y;
    pasoRuta = 0;
  }

  // 4. Enviar telemetría al Gemelo Digital en PyBullet: "POS,id,x,y"
  char telemetria[32];
  snprintf(telemetria, sizeof(telemetria), "POS,%d,%d,%d", NODO_ID, posX, posY);
  udp.beginPacket(broadcastIP, UDP_PORT);
  udp.write((const uint8_t *)telemetria, strlen(telemetria));
  udp.endPacket();

  delay(350); // Tasa de movimiento visualizable en PyBullet
}