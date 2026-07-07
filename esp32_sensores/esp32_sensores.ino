#include <LiquidCrystal.h>

// LCD JHD 162A en modo 4-bit: RS=13, E=14, D4=25, D5=26, D6=27, D7=33
LiquidCrystal lcd(13, 14, 25, 26, 27, 33);

void setup() {
  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("Hola ESP32!");
  lcd.setCursor(0, 1);
  lcd.print("LCD funcionando");
}

void loop() {}
