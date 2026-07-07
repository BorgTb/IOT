#include <SPI.h>
#include <WiFi101.h>
#include <PubSubClient.h>
#include <LiquidCrystal.h>

// CONFIGURACION DE WI-FI Y MQTT
const char* ssid = "iPhoneTintin";
const char* password = "agu12355";
const char* mqtt_server = "172.20.10.3";
const int mqtt_port = 1883;

// CREDENCIALES MQTT
const char* mqtt_user = "mkr1000";
const char* mqtt_pass = "mkr1000_iot";

WiFiClient mkrClient;
PubSubClient client(mkrClient);

// DEFINICION DE PINES Y VARIABLES DE SENSORES
const int pinMaxBotix = A0;
const int pinMQ       = A1;
const int pinMAX4466  = A2;

// LCD JHD 162A en modo 4-bit: RS=5, E=6, D4=7, D5=8, D6=9, D7=10
LiquidCrystal lcd(5, 6, 7, 8, 9, 10);

// UMBRALES DE ALERTA (ajustar segun los mismos valores que usa Node-RED)
const int    UMBRAL_CO2       = 400;  // valor ADC raw
const int    UMBRAL_SONIDO    = 70;   // porcentaje
const float  UMBRAL_DISTANCIA = 30.0; // cm

// DEFINICION DE PINES Y ESTADO DEL LED
const int pinLED = 4;

bool estadoLED = false;
bool estadoLEDCambio = false;

float distanciaAnterior = 0;

// TOPICS MQTT (sensores reales: CO2 (MQ7), sonido, distancia ultrasonica)
const char* topicCO2        = "smarthome/equipo2/co2";
const char* topicSonido     = "smarthome/equipo2/sonido";
const char* topicDistancia  = "smarthome/equipo2/distancia";
const char* topicAlerta     = "smarthome/equipo2/alerta";
const char* topicLedSet     = "smarthome/equipo2/control/led";
const char* topicLedState   = "smarthome/equipo2/led/state";

const int sampleWindow = 50;
unsigned int sample;

unsigned long lastMsg = 0;
const long interval = 2000;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("Wi-Fi conectado.");
  Serial.print("Direccion IP: ");
  Serial.println(WiFi.localIP());
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String topico = String(topic);
  if (topico == topicLedSet) {
    String msg = "";
    for (unsigned int i = 0; i < length; i++) {
      msg += (char)payload[i];
    }
    msg.toUpperCase();
    if (msg == "ON") {
      estadoLED = true;
    } else if (msg == "OFF") {
      estadoLED = false;
    } else if (msg == "TOGGLE") {
      estadoLED = !estadoLED;
    }
    digitalWrite(pinLED, estadoLED ? HIGH : LOW);
    estadoLEDCambio = true;
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conexion MQTT...");
    String clientId = "MKR1000Client-";
    clientId += String(random(0, 1000));
    // CONEXION CON USUARIO Y CONTRASEÑA
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("Conectado!");
      client.subscribe(topicLedSet);
      client.publish(topicLedState, estadoLED ? "ON" : "OFF");
    } else {
      Serial.print("Fallo, rc=");
      Serial.print(client.state());
      Serial.println(" reintentando en 5s...");
      delay(5000);
    }
  }
}

void actualizarLCD(float dist, int co2, int sonido) {
  // Fila 0: valores de sensores (rotados cada ciclo para caber en 16 chars)
  lcd.setCursor(0, 0);
  lcd.print("D:");
  lcd.print((int)dist);
  lcd.print("cm G:");
  lcd.print(co2);
  lcd.print("  ");   // limpia restos de ciclo anterior

  // Fila 1: estado de alerta
  lcd.setCursor(0, 1);
  if (co2 > UMBRAL_CO2) {
    lcd.print("! ALERTA: GAS   ");
  } else if (sonido > UMBRAL_SONIDO) {
    lcd.print("! ALERTA: SONIDO");
  } else if (dist < UMBRAL_DISTANCIA) {
    lcd.print("! ALERTA: DIST. ");
  } else {
    lcd.print("S:");
    lcd.print(sonido);
    lcd.print("%  OK          ");
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; }
  Serial.println("Iniciando sistema IoT...");
  pinMode(pinLED, OUTPUT);
  digitalWrite(pinLED, LOW);

  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("Iniciando...");

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(512);
  client.setCallback(mqttCallback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  if (estadoLEDCambio) {
    client.publish(topicLedState, estadoLED ? "ON" : "OFF");
    estadoLEDCambio = false;
  }

  unsigned long now = millis();
  if (now - lastMsg > interval) {
    lastMsg = now;

    // 1. SENSOR ULTRASONICO (MaxBotix)
    long sumaMaxBotix = 0;
    for (int i = 0; i < 5; i++) {
      sumaMaxBotix += analogRead(pinMaxBotix);
      delay(5);
    }
    int valorMaxBotix = sumaMaxBotix / 5;
    const float VCC_SENSOR = 3.3;
    float voltajeSalida = (valorMaxBotix * 3.3) / 1023.0;
    float pulgadas = voltajeSalida / (VCC_SENSOR / 512.0);
    float distanciaCm = pulgadas * 2.54;
    if (distanciaCm < 15.0 || distanciaCm > 645.0) distanciaCm = distanciaAnterior;
    distanciaAnterior = distanciaCm;

    // 2. SENSOR DE CO2 (MQ7)
    int valorCO2 = analogRead(pinMQ);

    // 3. SENSOR DE SONIDO (GY-MAX4466)
    unsigned long startMillis = millis();
    unsigned int signalMax = 0;
    unsigned int signalMin = 1023;
    while (millis() - startMillis < sampleWindow) {
      sample = analogRead(pinMAX4466);
      if (sample < 1024) {
        if (sample > signalMax) signalMax = sample;
        else if (sample < signalMin) signalMin = sample;
      }
    }
    unsigned int peakToPeak = signalMax - signalMin;
    int porcentajeSonido = (peakToPeak * 100) / 1023;

    // 4. IMPRIMIR RESULTADOS
    Serial.print("Distancia: "); Serial.print(distanciaCm); Serial.print(" cm");
    Serial.print("\t| CO2 MQ7: "); Serial.print(valorCO2);
    Serial.print("\t| Sonido: "); Serial.println(porcentajeSonido);

    // 4b. ACTUALIZAR LCD
    actualizarLCD(distanciaCm, valorCO2, porcentajeSonido);

    // 5. PUBLICAR TOPICS
    client.publish(topicCO2,       String(valorCO2).c_str());
    client.publish(topicSonido,    String(porcentajeSonido).c_str());
    client.publish(topicDistancia, String(distanciaCm, 1).c_str());

    // 6. JSON COMBINADO (alerta/tipo para Node-RED)
    String tipoAlerta = "NINGUNA";
    if (valorCO2 > UMBRAL_CO2)           tipoAlerta = "GAS";
    else if (porcentajeSonido > UMBRAL_SONIDO) tipoAlerta = "SONIDO";
    else if (distanciaCm < UMBRAL_DISTANCIA)   tipoAlerta = "DISTANCIA";
    client.publish("smarthome/equipo2/alerta/tipo", tipoAlerta.c_str());

    // 7. JSON COMBINADO
    String payload = "{";
    payload += "\"distancia\": " + String(distanciaCm) + ", ";
    payload += "\"co2\": " + String(valorCO2) + ", ";
    payload += "\"sonido\": " + String(porcentajeSonido);
    payload += "}";
    client.publish(topicAlerta, payload.c_str());
  }
}