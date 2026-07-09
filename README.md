# SmartHome IoT — Unidades 1, 2 y 3

Sistema IoT de hogar inteligente con MQTT seguro, LLM local (Ollama), gemelo digital,
predicción de series de tiempo, agente autónomo y dashboards. Todo el stack corre en
contenedores con Docker Compose.

---

## 1. Arquitectura

```
[MKR1000 / ESP32-CAM]                         (sensores físicos + cámara)
        │ MQTT (co2, distancia, sonido, eventos)
        ▼
   ┌──────────┐   escribe    ┌──────────┐    consulta    ┌──────────┐
   │ Mosquitto│─────────────▶│ Node-RED │───────────────▶│  Ollama  │ (LLM local)
   │  (broker)│              │  Gemelo  │   prompt/JSON   │llama3.2  │
   └──────────┘              │  Digital │◀───────────────└──────────┘
        ▲  ▲                 │ + API    │   decisión
        │  │                 │ REST     │
        │  │                 └────┬─────┘
        │  │  escribe sensores    │ GET /gemelo/estado
        │  │                      ▼
        │  │                 ┌──────────┐   query 6h   ┌──────────┐
        │  └─────────────────│ InfluxDB │◀─────────────│ Predictor│ (numpy.polyfit)
        │   predicción MQTT  │ (TS DB)  │─────────────▶│  co2/dist│
        │                    └────┬─────┘   escribe     └──────────┘
        │                         │ datasource
        │                         ▼
        │                    ┌──────────┐
        │                    │ Grafana  │ (dashboards + alerta)
        │                    └──────────┘
        │ control (led)
        │                    ┌──────────┐  razona+actúa cada 2 min
        └────────────────────│   n8n    │ (agente autónomo)
                             │  Agente  │──▶ Ollama / Node-RED / InfluxDB
                             └──────────┘
```

## 2. Servicios (Docker Compose)

| Servicio | Puerto | Descripción |
|---|---|---|
| `mosquitto` | 1883 / 8883 | Broker MQTT (auth + TLS + ACLs) |
| `nodered` | 1880 | Gemelo digital, lógica LLM, API REST, dashboard |
| `ollama` | 11434 | LLM local (`llama3.2:3b`) |
| `influxdb` | 8086 | Base de datos de series de tiempo |
| `grafana` | 3000 | Dashboards + alertas |
| `n8n` | 5678 | Agente autónomo |
| `predictor` | — | Script Python de predicción (cada 2 min) |
| `coap-bridge` | 5683/udp | Servidor CoAP (`aiocoap`) que redirige a MQTT |
| `api-ia` | 5000 | Reconocimiento facial (ESP32-CAM → persona) |

---

## 3. Cómo ejecutar

### Requisitos
- Docker Desktop / Docker Engine + Docker Compose
- (primera vez) descargar el modelo LLM:

```bash
docker compose up -d ollama
docker exec ollama ollama pull llama3.2:3b
```
> `llama3.2:3b` (~2GB) es el modelo configurado en todos los flujos (Node-RED y n8n);
> da buenas respuestas en español. Si tu equipo es muy limitado puedes bajar a
> `qwen2.5:0.5b` (más rápido pero respuestas pobres) cambiando el `model` en los flujos.

### Levantar todo
```bash
docker compose up -d
docker ps --format "{{.Names}}: {{.Status}}"
```
Deben quedar arriba: `mosquitto, nodered, ollama, influxdb, grafana, n8n, predictor, api-ia`.

### Detener
```bash
docker compose down          # conserva datos (volúmenes)
docker compose down -v       # borra también los volúmenes
```

---

## 4. Accesos

| Servicio | URL | Login |
|---|---|---|
| Dashboard / Chat LLM | http://localhost:1880/ui | — |
| Node-RED (editor) | http://localhost:1880 | — |
| API Gemelo Digital | http://localhost:1880/gemelo/estado | — |
| Grafana | http://localhost:3000 | admin / admin |
| n8n (agente) | http://localhost:5678 | — |
| InfluxDB | http://localhost:8086 | admin / admin123 |

### Credenciales MQTT (ACLs en `mosquitto/config/acl.acl`)
| Usuario | Password | Permisos |
|---|---|---|
| `mkr1000` | `mkr1000_iot` | publica sensores, lee `control/#` |
| `predictor` | `predictor_iot` | publica `prediccion/#` y `alerta` |
| `esp32_cam` | `esp32_cam123` | `equipo1/camara/#` |
| `nodered` | (interno) | `equipo1/#`, `equipo2/#` |

---

## 5. Qué está implementado

### Unidad 2 — Protocolos, seguridad y LLM
- ✅ **MQTT con auth** (`mosquitto_passwd`) + **TLS** en 8883 + **ACLs** por cliente.
  Node-RED conecta al broker por **TLS (`mqtts://mosquitto:8883`)**.
- ✅ **LLM local (Ollama)** como controlador: Node-RED arma el prompt con el estado del
  hogar, llama a `/api/generate` con `format:json`, parsea y publica decisión/comandos MQTT
  (a `smarthome/equipo2/...`).
- ✅ **Consulta en lenguaje natural** en el dashboard (`/ui`), publica a `llm/respuesta`.
- ✅ **CoAP**: nodo sensor (`esp32/esp32_coap_sensor.ino`) → servicio **`coap-bridge`**
  (`aiocoap`, UDP 5683) que redirige los recursos CoAP al broker MQTT.

### Unidad 3 — Gemelo digital, predicción y agente
- ✅ **Gemelo digital** como objeto JSON con historial + API REST `GET /gemelo/estado`.
- ✅ **Node-RED → InfluxDB**: cada lectura de sensor se guarda (measurement `sensor`).
- ✅ **Predictor** (`unidad3/predictor/predict.py`): regresión lineal a 30 min sobre datos
  reales, publica a MQTT + gemelo + InfluxDB (measurement `prediccion`).
- ✅ **Grafana**: datasource + dashboard *"SmartHome IoT - Unidad 3"* (histórico,
  predicción superpuesta, estado, log del agente) + **alerta** "CO2 alto (>400 ppm)".
- ✅ **Agente autónomo n8n** (`unidad3/n8n/agente-autonomo.json`): cada 2 min consulta el
  gemelo, razona con el LLM, ejecuta acciones en cadena (actuadores vía Node-RED) y
  registra el log en InfluxDB.

---

## 6. Cómo probar (demo rápida)

> Guía detallada en **[PRUEBAS.md](PRUEBAS.md)**.

**Inyectar un dato de sensor y verlo propagarse:**
```bash
docker exec mosquitto mosquitto_pub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t smarthome/equipo2/alerta -m '{"distancia":45,"co2":512,"sonido":77}'
curl -s http://localhost:1880/gemelo/estado
```

**Chat:** en http://localhost:1880/ui escribe *"Resume el estado del hogar"*.

**Predictor:**
```bash
docker logs --tail 5 predictor          # -> "Prediccion co2 30min: ... ppm"
```

**Agente actuando en cadena (lo más vistoso):**
```bash
# fuerza co2 crítico
docker exec mosquitto mosquitto_pub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t smarthome/equipo2/alerta -m '{"co2":600,"distancia":50,"sonido":40}'
# escucha actuadores (deja corriendo en otra terminal)
docker exec mosquitto mosquitto_sub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t 'smarthome/equipo2/control/#' -v
```

**Probar la acción en cadena directamente (sin esperar el ciclo):**
```bash
curl -s -X POST http://localhost:1880/agente/accion \
  -H "Content-Type: application/json" -d '{"dispositivo":"led","estado":true}'
```

**Verificar InfluxDB:**
```bash
docker exec influxdb influx query \
 'from(bucket:"sensores")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="sensor")|>last()' \
 --org smarthome --token smarthome_token_2024
```

---

## 7. Estructura del repositorio

```
.
├── docker-compose.yml            # stack completo
├── Dockerfile                    # imagen de Node-RED
├── README.md                     # este archivo
├── PRUEBAS.md                    # guía de pruebas paso a paso
├── mosquitto/
│   ├── config/                   # mosquitto.conf, acl.acl, passwd
│   └── certs/                    # certificados TLS (CA + broker)
├── node-red-data/
│   └── flows.json                # gemelo digital, LLM, API REST, endpoints agente/grafana
├── esp32/                        # firmwares ESP32 (MQTT TLS, CoAP)
├── ProyectoIOT/                  # firmware MKR1000 (sensores)
├── api-ia/                       # API reconocimiento facial (Flask)
└── unidad3/
    ├── predictor/                # predict.py + Dockerfile
    ├── n8n/                      # agente-autonomo.json
    └── grafana/                  # provisioning (datasource, dashboard, alerta)
```

---

## 8. Notas y troubleshooting

- **El gemelo muestra valores por defecto:** ocurre justo tras reiniciar Node-RED; se
  refresca con el siguiente mensaje de sensor (cada 2 s si el MKR1000 está encendido).
- **Sensores reales (4):** CO2 (MQ7), nivel de sonido, distancia ultrasónica, y la
  ESP32-CAM (detección de persona + reconocimiento facial vía `api-ia`).
- **El agente solo acciona en condición crítica** (co2 > 400, sonido > 80, distancia < 20).
- **MKR1000 con firmware viejo:** si aún publica `gas` en vez de `co2`, Node-RED lo acepta
  igual (mapea `gas`→`co2`); reflashea el firmware para que publique `co2` directamente.
- **Tópicos de control:** los sensores/actuadores reales del MKR1000 usan `equipo2`; el
  endpoint `/agente/accion` y el agente publican en `smarthome/equipo2/control/...`.
- **Reimportar el agente n8n** (si se borra):
  ```bash
  docker cp unidad3/n8n/agente-autonomo.json n8n:/tmp/agente.json
  docker exec n8n n8n import:workflow --input=/tmp/agente.json
  docker restart n8n
  ```
