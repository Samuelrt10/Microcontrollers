#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>

// Configuración de la pantalla LCD I2C (0x27 o 0x3F son las direcciones más comunes)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Configuración del mapa del teclado matricial 4x4
const byte ROWS = 4; 
const byte COLS = 4; 

char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};

// Pines del ESP32 conectados al teclado (Verifica las conexiones físicas de tu montaje)
byte rowPins[ROWS] = {19, 18, 5, 17}; 
byte colPins[COLS] = {16, 4, 2, 15}; 

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

void setup() {
  // Inicializar comunicación serial a 9600 baudios (debe coincidir con main.py)
  Serial.begin(9600); 
  
  // Inicializar la pantalla LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Esperando dato..");
}

void loop() {
  // Leer la tecla presionada
  char key = keypad.getKey();

  if (key) {
    // 1. Actualizar la interfaz local (LCD)
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Enviando trazo:");
    lcd.setCursor(7, 1);
    lcd.print(key);

    // 2. Enviar el comando al PC (Python) vía USB
    Serial.println(key);
    
    // Pequeño retardo para evitar rebotes físicos del botón
    delay(200);
  }
}