# Unidad 1 — SmartHome IoT

Sistema de automatización y monitoreo para una casa inteligente.
Esta carpeta contiene **todos los entregables de código de la Unidad 1**, recuperados de los respaldos que quedaron al migrar el proyecto a las Unidades 2 y 3.

## Estructura de la carpeta

```
unidad1/
├── docker-compose.yml        # Mosquitto + Node-RED + API de reconocimiento facial
├── Dockerfile                # Imagen personalizada de Node-RED (dashboard, telegram, sqlite, tfjs)
├── mosquitto/
│   └── mosquitto.conf        # Broker MQTT (puerto 1883, sin TLS — la seguridad se agregó en U2)
├── firmware/
│   ├── ProyectoIOT.ino       # Nodo de sensores (Arduino MKR1000)
│   └── esp32cam.ino          # ESP32-CAM: stream MJPEG + captura de snapshot
├── api-ia/
│   ├── app.py                # API Flask de reconocimiento facial (face_recognition + OpenCV)
│   ├── Dockerfile
│   └── requirements.txt
└── nodered/
    └── flows.json            # Flujo completo de Node-RED (importar en http://localhost:1880)
```

## Arquitectura

```
MKR1000 (sensores) ──MQTT──► Mosquitto ──► Node-RED ──► Dashboard / Telegram / SQLite
ESP32-CAM ──HTTP (/capture, /stream)──► Node-RED ──HTTP──► api-ia (/recognize)
                                            │
                                            └──MQTT──► smarthome/equipo1/camara/evento
```

## 1. Nodo de sensores — `firmware/ProyectoIOT.ino`

Arduino MKR1000 con WiFi101 + PubSubClient. Lee y publica:

| Sensor | Pin | Tópico MQTT |
|---|---|---|
| CO2 / gas (MQ7) | A1 | `smarthome/equipo2/co2` |
| Sonido (MAX4466) | A2 | `smarthome/equipo2/sonido` |
| Distancia ultrasónica (MaxBotix, sensor diferencial) | A0 | `smarthome/equipo2/distancia` |
| Alerta (JSON con todas las variables) | — | `smarthome/equipo2/alerta` |

Actuador: LED en pin 4, controlado por `smarthome/equipo2/control/led` y reportando estado en `smarthome/equipo2/led/state`.

## 2. Detección facial (cámara + IA)

Este es el subsistema que faltaba consolidar. Se compone de **tres piezas**:

### a) `firmware/esp32cam.ino` — ESP32-CAM (AI-Thinker)

Levanta un servidor HTTP con dos endpoints:

- `GET /stream` — stream MJPEG en vivo (se muestra en el dashboard).
- `GET /capture` — snapshot JPEG único (lo consume Node-RED para el reconocimiento).

La cámara **solo captura y transmite**; la detección ocurre en el servidor, como pide el enunciado.

### b) `api-ia/app.py` — API de reconocimiento facial

Servicio Flask (puerto 5000) que usa `face_recognition` (dlib) + OpenCV. Mantiene una base de rostros conocidos en `imagenes_db/<Nombre>/rostro_N.jpg`. Endpoints principales:

- `POST /recognize` — recibe imagen base64, devuelve rostros detectados con nombre, confianza y bounding box.
- `POST /train` — registra una persona nueva desde el formulario del dashboard.
- `GET /faces`, `DELETE /faces/<nombre>`, `POST /sync`, `GET /health` — gestión de la base de rostros.

Esto no solo detecta **si hay una persona** sino **quién es** (requisito del problema: "identificar si hay una persona presente y quién es esa persona"). La imagen de Node-RED igualmente incluye `node-red-contrib-tfjs-coco-ssd` por si se quiere usar la detección genérica de personas con TensorFlow.js.

### c) `nodered/flows.json` — Flujo de detección en Node-RED

Cadena principal (pestaña *Alertas + Control LED*):

```
inject "Capturar cada 2s"
  → http request GET http://<IP-ESP32CAM>/capture
  → function "Buffer a Base64 JSON"
  → http request POST http://api-ia:5000/recognize
  → function "Evaluar Rostros"
       ├─ persona conocida  → publica {"equipo":"equipo1","alerta":"persona_identificada","identidad":"<nombre>"}
       └─ desconocido       → publica {"equipo":"equipo1","alerta":"intruso_detectado"}
  → mqtt out  smarthome/equipo1/camara/evento
  → notificación Telegram + texto en dashboard
```

Además el flujo incluye:

- **Dashboard** (FlowFuse Dashboard 2.0): valores actuales de gas, sonido, distancia, movimiento y persona detectada, vista de cámara en vivo (`/stream`), botón de captura manual, switch de LED, indicador de estado del sistema y gráfico histórico de gas.
- **Registro de personal**: formulario que envía fotos a `POST /train` para dar de alta rostros nuevos.
- **Control automático**: reglas por umbral en la función "Verificar umbrales" (gas/sonido/distancia) y regla de intruso (rostro desconocido → alerta + Telegram).
- **Notificaciones externas**: bot de Telegram (alertas de umbral, eventos de cámara y comando `/led`).
- **Registro histórico**: inserciones en SQLite con timestamp, valores de sensores y estado de alerta, con consulta por rango desde el dashboard.

## 3. Puesta en marcha

```bash
cd unidad1
docker compose up -d --build
```

1. Node-RED: `http://localhost:1880` — si el volumen está vacío, importar `nodered/flows.json` (Menú → Import).
2. Dashboard: `http://localhost:1880/dashboard`.
3. API IA: `http://localhost:5000/health` para verificar que cargó los rostros.
4. Flashear `firmware/ProyectoIOT.ino` (MKR1000) y `firmware/esp32cam.ino` (ESP32-CAM) con las credenciales WiFi y la IP del broker de la red local.
5. Ajustar en el flujo la URL del nodo `GET /capture` con la IP que la ESP32-CAM imprime por serial.

> **Nota:** las IPs incluidas (broker `172.20.10.3`, cámara `172.20.10.8`) corresponden al hotspot usado en la demo; deben actualizarse según la red donde se despliegue.
