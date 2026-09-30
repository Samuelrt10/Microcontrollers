#include <SPI.h>

// Definición estricta de pines para la ESP32-S3
#define S3_SCK  12
#define S3_MISO 13
#define S3_MOSI 11
#define S3_CS   10

void setup() {
  // Inicializa el puerto serial para escuchar a Python
  Serial.begin(9600);
  
  // Inicializa el bus SPI hacia el Esclavo
  SPI.begin(S3_SCK, S3_MISO, S3_MOSI, S3_CS);
  pinMode(S3_CS, OUTPUT);
  digitalWrite(S3_CS, HIGH); // Bus inactivo por defecto
}

void loop() {
  // Si llega un dato desde Python por el cable USB
  if (Serial.available() > 0) {
    char digitoRecibido = Serial.read();
    
    // Configurar velocidad estable comprobada (100 kHz)
    SPI.beginTransaction(SPISettings(100000, MSBFIRST, SPI_MODE0));
    
    // Iniciar transmisión SPI al Esclavo
    digitalWrite(S3_CS, LOW);
    SPI.transfer(digitoRecibido); 
    digitalWrite(S3_CS, HIGH);
    
    SPI.endTransaction();
  }
}