/*
 * ESP32-2432S024 ("esp32-024", pantalla ST7789 2.4" tipo CYD)
 * Panel de visualizacion estilo Grafana para los sensores del equipo2.
 *
 * Se conecta por MQTT y muestra:
 *   - Pantalla 1: valores actuales + decision de la IA + alertas recientes
 *   - Pantalla 2: graficos en tiempo real de CO2, distancia y sonido
 *     (las mismas series que muestra Grafana, dibujadas localmente)
 * El boton BOOT (GPIO0) alterna entre ambas pantallas.
 *
 * Los umbrales NO estan hardcodeados: se suscribe a los umbrales retenidos
 * (smarthome/equipo2/umbrales/#), los mismos que se cambian desde el chat
 * LLM o Telegram, asi la pantalla siempre colorea con el limite vigente.
 *
 * Librerias (Arduino Library Manager):
 *   - TFT_eSPI (Bodmer)
 *   - PubSubClient
 *   - ArduinoJson (v6 o v7)
 *
 * Usuario MQTT: "display" (lectura de alerta, llm/decision y umbrales).
 * Ya esta dado de alta en mosquitto/config/passwd y acl.acl.
 */

#define USER_SETUP_LOADED 1
#define ST7789_DRIVER
#define TFT_WIDTH   240
#define TFT_HEIGHT  320
#define TFT_MOSI 13
#define TFT_SCLK 14
#define TFT_CS   15
#define TFT_DC    2
#define TFT_RST  -1
#define TFT_BL   27
#define TFT_BACKLIGHT_ON HIGH
#define TFT_RGB_ORDER TFT_BGR
#define TFT_INVERSION_ON
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF
#define SPI_FREQUENCY       40000000
#define SPI_READ_FREQUENCY  20000000

#include <SPI.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

TFT_eSPI tft = TFT_eSPI();

// ─── WiFi y MQTT ──────────────────────────────────────
const char* ssid        = "iPhoneTintin";
const char* password    = "agu12355";
const char* mqtt_server = "172.20.10.4";
const int   mqtt_port   = 1883;

const char* mqtt_user = "display";
const char* mqtt_pass = "esp32_display123";
const char* mqtt_client_id_prefix = "ESP32-024-";

const char* topicAlerta   = "smarthome/equipo2/alerta";
const char* topicDecision = "smarthome/equipo2/llm/decision";
const char* topicUmbrales = "smarthome/equipo2/umbrales/#";

WiFiClient espClient;
PubSubClient client(espClient);

// ─── Boton fisico (BOOT) para cambiar de pantalla ────
#define PIN_BOTON 0
unsigned long ultimoCambioBoton = 0;
const unsigned long DEBOUNCE_MS = 250;

// ─── Umbrales dinamicos (llegan retenidos por MQTT) ───
float umbralCO2       = 400;
float umbralSonido    = 80;
float umbralDistancia = 20;
const unsigned long COOLDOWN_ALERTA_MS = 15000;
unsigned long ultimaAlertaCO2 = 0, ultimaAlertaSonido = 0, ultimaAlertaDistancia = 0;

// ─── Estado de sensores ───────────────────────────────
float co2 = 0, distancia = 0, sonido = 0;
unsigned long ultimoDato = 0;
bool datosNuevos = false;

String nivelLLM = "normal";
String razonLLM = "Esperando datos...";

#define MAX_ALERTAS 5
String alertas[MAX_ALERTAS];
int numAlertas = 0;

// ─── Historial para los graficos ──────────────────────
#define MAX_PUNTOS 120
float histCO2[MAX_PUNTOS];
float histDist[MAX_PUNTOS];
float histSonido[MAX_PUNTOS];
int totalHist = 0;

// ─── Pantallas ─────────────────────────────────────────
enum Pantalla { PANTALLA_VALORES, PANTALLA_GRAFICO };
Pantalla pantallaActual = PANTALLA_VALORES;
bool pantallaDirty = true;

void agregarAlerta(String msg) {
  for (int i = MAX_ALERTAS - 1; i > 0; i--) alertas[i] = alertas[i - 1];
  alertas[0] = msg;
  if (numAlertas < MAX_ALERTAS) numAlertas++;
}

void evaluarUmbrales() {
  unsigned long ahora = millis();
  if (co2 > umbralCO2 && ahora - ultimaAlertaCO2 > COOLDOWN_ALERTA_MS) {
    agregarAlerta("Gas alto: " + String(co2, 0) + " (limite " + String(umbralCO2, 0) + ")");
    ultimaAlertaCO2 = ahora;
  }
  if (sonido > umbralSonido && ahora - ultimaAlertaSonido > COOLDOWN_ALERTA_MS) {
    agregarAlerta("Sonido alto: " + String(sonido, 0) + " (limite " + String(umbralSonido, 0) + ")");
    ultimaAlertaSonido = ahora;
  }
  if (distancia < umbralDistancia && ahora - ultimaAlertaDistancia > COOLDOWN_ALERTA_MS) {
    agregarAlerta("Distancia baja: " + String(distancia, 1) + " cm (limite " + String(umbralDistancia, 0) + ")");
    ultimaAlertaDistancia = ahora;
  }
}

void guardarHistorial() {
  if (totalHist < MAX_PUNTOS) {
    histCO2[totalHist]    = co2;
    histDist[totalHist]   = distancia;
    histSonido[totalHist] = sonido;
    totalHist++;
  } else {
    for (int i = 1; i < MAX_PUNTOS; i++) {
      histCO2[i - 1]    = histCO2[i];
      histDist[i - 1]   = histDist[i];
      histSonido[i - 1] = histSonido[i];
    }
    histCO2[MAX_PUNTOS - 1]    = co2;
    histDist[MAX_PUNTOS - 1]   = distancia;
    histSonido[MAX_PUNTOS - 1] = sonido;
  }
}

uint16_t colorNivel(const String& nivel) {
  if (nivel == "critico") return TFT_RED;
  if (nivel == "medio")   return TFT_ORANGE;
  return TFT_GREEN;
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) return;

  String t = String(topic);
  if (t == topicAlerta) {
    if (doc.containsKey("co2"))        co2 = doc["co2"].as<float>();
    else if (doc.containsKey("gas"))   co2 = doc["gas"].as<float>();
    if (doc.containsKey("distancia"))  distancia = doc["distancia"].as<float>();
    if (doc.containsKey("sonido"))     sonido = doc["sonido"].as<float>();

    ultimoDato = millis();
    guardarHistorial();
    evaluarUmbrales();
    datosNuevos = true;
  } else if (t == topicDecision) {
    if (doc.containsKey("nivel"))         nivelLLM = doc["nivel"].as<String>();
    if (doc.containsKey("razonamiento"))  razonLLM = doc["razonamiento"].as<String>();
    if (nivelLLM != "normal") agregarAlerta("IA (" + nivelLLM + "): " + razonLLM);
    datosNuevos = true;
  } else if (t.startsWith("smarthome/equipo2/umbrales/")) {
    // Umbrales retenidos: los mismos que ajusta la IA desde el chat/Telegram
    if (!doc.containsKey("limite")) return;
    float limite = doc["limite"].as<float>();
    String sensor = t.substring(t.lastIndexOf('/') + 1);
    if      (sensor == "co2")       umbralCO2 = limite;
    else if (sensor == "sonido")    umbralSonido = limite;
    else if (sensor == "distancia") umbralDistancia = limite;
    datosNuevos = true;
  }
}

void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(300);
}

void mqttReconnect() {
  while (!client.connected()) {
    String clientId = mqtt_client_id_prefix + String(random(0, 1000));
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      client.subscribe(topicAlerta);
      client.subscribe(topicDecision);
      client.subscribe(topicUmbrales);
    } else {
      delay(2000);
    }
  }
}

// ─── Dibujo: pantalla de valores ───────────────────────
void dibujarPantallaValores(bool full) {
  if (full) {
    tft.fillScreen(TFT_BLACK);
    tft.fillRect(0, 0, tft.width(), 26, TFT_NAVY);
    tft.setTextColor(TFT_WHITE, TFT_NAVY);
    tft.setTextFont(4);
    tft.drawString("MONITOR SENSORES", 8, 4);
  }

  int y = 36;
  tft.setTextFont(4);

  tft.fillRect(0, y, tft.width(), 30, TFT_BLACK);
  tft.setTextColor(co2 > umbralCO2 ? TFT_RED : TFT_GREEN, TFT_BLACK);
  tft.drawString("Gas (CO2): " + String(co2, 0) + " / " + String(umbralCO2, 0), 8, y);

  y += 32;
  tft.fillRect(0, y, tft.width(), 30, TFT_BLACK);
  tft.setTextColor(distancia < umbralDistancia ? TFT_RED : TFT_GREEN, TFT_BLACK);
  tft.drawString("Dist: " + String(distancia, 1) + " / " + String(umbralDistancia, 0) + " cm", 8, y);

  y += 32;
  tft.fillRect(0, y, tft.width(), 30, TFT_BLACK);
  tft.setTextColor(sonido > umbralSonido ? TFT_RED : TFT_GREEN, TFT_BLACK);
  tft.drawString("Sonido: " + String(sonido, 0) + " / " + String(umbralSonido, 0), 8, y);

  y += 36;
  tft.setTextFont(2);
  tft.setTextColor(colorNivel(nivelLLM), TFT_BLACK);
  tft.fillRect(0, y, tft.width(), 34, TFT_BLACK);
  tft.drawString("IA [" + nivelLLM + "]: " + razonLLM, 8, y, 2);

  y += 40;
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("Alertas recientes:", 8, y);
  y += 18;

  tft.fillRect(0, y, tft.width(), tft.height() - y - 16, TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  for (int i = 0; i < numAlertas; i++) {
    tft.drawString(alertas[i], 8, y + i * 18);
  }

  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString("Boton BOOT: ver graficos", 8, tft.height() - 16);
}

// ─── Dibujo: pantalla de graficos (estilo Grafana) ─────
void dibujarPanel(float* datos, int n, const char* etiqueta, uint16_t color, int yTop, int panelH) {
  const int margenIzq = 6;
  const int anchoGrafico = tft.width() - margenIzq - 4;

  tft.drawRect(margenIzq, yTop, anchoGrafico, panelH, TFT_DARKGREY);
  tft.setTextFont(2);
  tft.setTextColor(color, TFT_BLACK);
  tft.drawString(etiqueta, margenIzq + 2, yTop - 16);

  if (n < 2) return;

  float minV = datos[0], maxV = datos[0];
  for (int i = 1; i < n; i++) {
    if (datos[i] < minV) minV = datos[i];
    if (datos[i] > maxV) maxV = datos[i];
  }
  if (maxV - minV < 1.0) { maxV += 1.0; minV -= 1.0; }
  float margen = (maxV - minV) * 0.1;
  minV -= margen;
  maxV += margen;

  tft.setTextColor(color, TFT_BLACK);
  tft.drawRightString(String(datos[n - 1], 1), tft.width() - 6, yTop - 16, 2);

  int prevX = -1, prevY = -1;
  for (int i = 0; i < n; i++) {
    int x = margenIzq + (int)((float)i / (MAX_PUNTOS - 1) * anchoGrafico);
    int yNorm = (int)((datos[i] - minV) / (maxV - minV) * (panelH - 4));
    int y = yTop + panelH - 2 - yNorm;
    if (prevX >= 0) tft.drawLine(prevX, prevY, x, y, color);
    prevX = x;
    prevY = y;
  }
}

void dibujarPantallaGrafico(bool full) {
  if (full) {
    tft.fillScreen(TFT_BLACK);
    tft.fillRect(0, 0, tft.width(), 26, TFT_NAVY);
    tft.setTextColor(TFT_WHITE, TFT_NAVY);
    tft.setTextFont(4);
    tft.drawString("GRAFICO EN TIEMPO REAL", 8, 4);
  }

  int alto = tft.height();
  int alturaUtil = alto - 26 - 16;
  int panelH = alturaUtil / 3 - 20;
  int y0 = 26 + 22;

  tft.fillRect(0, 26, tft.width(), alturaUtil + 20, TFT_BLACK);

  dibujarPanel(histCO2,    totalHist, "Gas (CO2)",  TFT_CYAN,    y0, panelH);
  dibujarPanel(histDist,   totalHist, "Distancia",  TFT_YELLOW,  y0 + (panelH + 20), panelH);
  dibujarPanel(histSonido, totalHist, "Sonido",     TFT_MAGENTA, y0 + 2 * (panelH + 20), panelH);

  tft.setTextFont(2);
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString("Boton BOOT: ver valores", 8, tft.height() - 14);
}

void chequearBoton() {
  if (digitalRead(PIN_BOTON) == LOW) {
    unsigned long ahora = millis();
    if (ahora - ultimoCambioBoton > DEBOUNCE_MS) {
      ultimoCambioBoton = ahora;
      pantallaActual = (pantallaActual == PANTALLA_VALORES) ? PANTALLA_GRAFICO : PANTALLA_VALORES;
      pantallaDirty = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BOTON, INPUT_PULLUP);

  tft.init();
  tft.setRotation(1); // Si la imagen queda al reves, probar con 3
  tft.fillScreen(TFT_BLACK);
  tft.setTextFont(4);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Conectando WiFi...", 8, 8);

  setupWifi();

  tft.drawString("WiFi OK, conectando MQTT...", 8, 40);
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setBufferSize(512);
}

void loop() {
  if (!client.connected()) mqttReconnect();
  client.loop();

  chequearBoton();

  bool debeRedibujar = pantallaDirty || datosNuevos;
  if (debeRedibujar) {
    if (pantallaActual == PANTALLA_VALORES) {
      dibujarPantallaValores(pantallaDirty);
    } else {
      dibujarPantallaGrafico(pantallaDirty);
    }
    pantallaDirty = false;
    datosNuevos = false;
  }
}
