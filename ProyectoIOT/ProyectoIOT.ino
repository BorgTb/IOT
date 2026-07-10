#include <SPI.h>
#include <WiFi101.h>
#include <PubSubClient.h>
#include <WiFiUDP.h>
#include <coap-simple.h>

// CONFIGURACION DE WI-FI Y MQTT
const char* ssid = "iPhoneTintin";
const char* password = "agu12355";
const char* mqtt_server = "172.20.10.4";
const int mqtt_port = 1883;

// CREDENCIALES MQTT
const char* mqtt_user = "mkr1000";
const char* mqtt_pass = "mkr1000_iot";

WiFiClient mkrClient;
PubSubClient client(mkrClient);

WiFiUDP udp;
Coap coap(udp);

const char* coap_host = "192.168.1.10";
const int coap_port = 5683;

// PINES SENSORES Y LED
const int pinMaxBotix = A0;
const int pinMQ       = A1;
const int pinMAX4466  = A2;
const int pinLED      = 4;

const int pinLEDDist  = 11;
const int pinLEDGas   = 10;
const int pinLEDSon   = 12;

bool estadoLED = false;
bool estadoLEDCambio = false;
float distanciaAnterior = 0;

unsigned long ultimaAlarmaDist = 0;
unsigned long ultimaAlarmaGas  = 0;
unsigned long ultimaAlarmaSon  = 0;
const unsigned long TIEMPO_LED_ALARMA = 30000;

// UMBRALES DE ALARMA (iguales que Node-RED)
const float  UMBRAL_DIST   = 20.0;
const int    UMBRAL_CO2    = 500;
const int    UMBRAL_SONIDO = 80;

// TOPICS MQTT
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
  Serial.print("Conectando WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" OK");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String topico = String(topic);
  if (topico == topicLedSet) {
    String msg = "";
    for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
    msg.toUpperCase();
    if      (msg == "ON")     estadoLED = true;
    else if (msg == "OFF")    estadoLED = false;
    else if (msg == "TOGGLE") estadoLED = !estadoLED;
    digitalWrite(pinLED, estadoLED ? HIGH : LOW);
    estadoLEDCambio = true;
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.println("Reconectando MQTT...");
    String clientId = "MKR1000Client-" + String(random(0, 1000));
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      client.subscribe(topicLedSet);
      client.publish(topicLedState, estadoLED ? "ON" : "OFF");
      Serial.println("MQTT reconectado");
    } else {
      delay(5000);
    }
  }
}

void callbackCoapResp(CoapPacket &packet, IPAddress ip, int port) {}

void setup() {
  Serial.begin(9600);
  pinMode(pinLED, OUTPUT);
  digitalWrite(pinLED, LOW);

  pinMode(pinLEDDist, OUTPUT);
  pinMode(pinLEDGas, OUTPUT);
  pinMode(pinLEDSon, OUTPUT);
  digitalWrite(pinLEDDist, LOW);
  digitalWrite(pinLEDGas, LOW);
  digitalWrite(pinLEDSon, LOW);

  setup_wifi();

  coap.response(callbackCoapResp);
  coap.start();
  Serial.println("CoAP iniciado");

  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(512);
  client.setCallback(mqttCallback);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  coap.loop();

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

    // 4. CONTROL DE LEDS DE ALARMA (30s encendidos)
    unsigned long ahora = millis();
    if (distanciaCm < UMBRAL_DIST)   ultimaAlarmaDist = ahora;
    if (valorCO2 > UMBRAL_CO2)       ultimaAlarmaGas  = ahora;
    if (porcentajeSonido > UMBRAL_SONIDO) ultimaAlarmaSon = ahora;

    digitalWrite(pinLEDDist, (ahora - ultimaAlarmaDist < TIEMPO_LED_ALARMA) ? HIGH : LOW);
    digitalWrite(pinLEDGas,  (ahora - ultimaAlarmaGas  < TIEMPO_LED_ALARMA) ? HIGH : LOW);
    digitalWrite(pinLEDSon,  (ahora - ultimaAlarmaSon < TIEMPO_LED_ALARMA) ? HIGH : LOW);

    // 5. IMPRIMIR RESULTADOS
    Serial.print("Distancia: "); Serial.print(distanciaCm); Serial.print(" cm");
    Serial.print("\t| CO2: "); Serial.print(valorCO2);
    Serial.print("\t| Sonido: "); Serial.println(porcentajeSonido);

    // 6. PUBLICAR TOPICS
    client.publish(topicCO2,       String(valorCO2).c_str());
    client.publish(topicSonido,    String(porcentajeSonido).c_str());
    client.publish(topicDistancia, String(distanciaCm, 1).c_str());

    // 7. JSON COMBINADO
    String payload = "{";
    payload += "\"distancia\": " + String(distanciaCm) + ", ";
    payload += "\"co2\": " + String(valorCO2) + ", ";
    payload += "\"sonido\": " + String(porcentajeSonido);
    payload += "}";
    client.publish(topicAlerta, payload.c_str());

    // 8. COAP - enviar datos al bridge
    String jsonCO2 = "{\"valor\": " + String(valorCO2) + ", \"tipo\": \"co2\"}";
    String jsonSonido = "{\"valor\": " + String(porcentajeSonido) + ", \"tipo\": \"sonido\"}";
    String jsonDist = "{\"valor\": " + String(distanciaCm, 1) + ", \"tipo\": \"distancia\"}";
    coap.put(IPAddress(192, 168, 1, 10), coap_port, "/distancia", jsonDist.c_str());
    coap.put(IPAddress(192, 168, 1, 10), coap_port, "/co2", jsonCO2.c_str());
    coap.put(IPAddress(192, 168, 1, 10), coap_port, "/sonido", jsonSonido.c_str());
  }
}
