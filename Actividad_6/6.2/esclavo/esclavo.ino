#include <ESP32SPISlave.h>
#include <U8g2lib.h>
#include <Wire.h>

// DEJA DESCOMENTADA SOLO LA QUE TE FUNCIONÓ (SSD1306 o SH1106)
// U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

ESP32SPISlave slave;
uint8_t rx_buf[1]; 
char digitoMostrar = ' ';

void setup() {
  Serial.begin(9600);
  
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB10_tr); 
  u8g2.drawStr(10, 35, "Esperando...");
  u8g2.sendBuffer();
  
  slave.setDataMode(SPI_MODE0);
  
  // FORZAR EL BUS VSPI Y LOS PINES FÍSICOS EXACTOS EN LA CLÁSICA
  // begin(bus, sck, miso, mosi, cs)
  slave.begin(VSPI, 18, 19, 23, 5); 
  
  Serial.println("Esclavo SPI configurado. Esperando datos...");
}

void loop() {
  // 1. Preparamos el buffer para recibir 1 byte
  slave.queue(NULL, rx_buf, 1);
  
  // 2. Función de bloqueo: El código se detiene aquí hasta que el Maestro transmita
  slave.wait(); 
  
  // 3. Procesar el dato recibido
  digitoMostrar = (char)rx_buf[0];
  Serial.print("Dato SPI recibido: ");
  Serial.println(digitoMostrar);
  
  // Filtro de seguridad para evitar dibujar basura eléctrica
  if (digitoMostrar >= '0' && digitoMostrar <= '9') {
    char texto_pantalla[2] = {digitoMostrar, '\0'};
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_logisoso42_tr); 
    u8g2.drawStr(45, 55, texto_pantalla);  
    u8g2.sendBuffer();
  }
}