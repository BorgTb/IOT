/*
 * ESP32 Sensor CoAP
 * Publica temperatura y humedad via CoAP (UDP puerto 5683)
 * Usa libreria: CoAP-simple-library
 * Hardware: DHT22 en GPIO 4
 */

#include <WiFi.h>
#include <CoAPClient.h>
#include <DHT.h>

const char* ssid = "iPhoneTintin";
const char* password = "agu12355";

// CoAP
CoAPClient coap;
IPAddress coapServer(172, 20, 10, 3); // IP del host donde corre coap-bridge (puerto UDP 5683)
const int coapPort = 5683;

// DHT22
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

void setup() {
    Serial.begin(115200);
    dht.begin();

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi OK");

    coap.setup();
}

void loop() {
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();

    if (isnan(temp) || isnan(hum)) {
        Serial.println("Error leyendo DHT");
        delay(5000);
        return;
    }

    String jsonTemp = "{\"sensor\":\"coap_esp32\",\"tipo\":\"temperatura\",\"valor\":" + String(temp) + ",\"unidad\":\"C\"}";
    String jsonHum = "{\"sensor\":\"coap_esp32\",\"tipo\":\"humedad\",\"valor\":" + String(hum) + ",\"unidad\":\"%\"}";

    coap.put(coapServer, coapPort, "temperatura", jsonTemp.c_str());
    coap.put(coapServer, coapPort, "humedad", jsonHum.c_str());

    Serial.printf("CoAP -> temp: %.1f C, hum: %.1f %%\n", temp, hum);

    delay(30000);
}
