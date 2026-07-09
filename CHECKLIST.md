# Checklist del proyecto — según el PDF (Unidad 2 y 3)

**Leyenda:** ✅ hecho · ⚠️ parcial · ❌ no hecho · 📄 va en el informe (documentación)

> Estado verificado al 2026-06-30, leyendo el código actual y probando el stack en vivo
> (9 contenedores, MQTT sobre TLS, CoAP→MQTT, InfluxDB, Grafana, n8n).

---

# UNIDAD 2 — Protocolos, Seguridad y LLM Local

## Objetivos específicos
- [x] ✅ 1. Mosquitto con auth usuario/contraseña y TLS
- [x] ✅ 2. Node-RED conectado al broker **con TLS (8883)** — verificado: `Connected nodered_llm@mqtts://mosquitto:8883`. Firmware ESP32 TLS con **CA real** (ya no placeholder)
- [x] ✅ 3. CoAP en un nodo sensor + recepción en el backend — **puente CoAP→MQTT funcional** (microservicio `aiocoap`)
- [x] ✅ 4. Ollama con modelo local (`llama3.2:3b`, buenas respuestas en español)
- [x] ✅ 5. LLM integrado en Node-RED reemplazando if/else
- [x] ✅ 6. Campo de consulta en lenguaje natural en el dashboard
- [ ] 📄 7. Documentar seguridad + analizar una vulnerabilidad (informe — esqueleto en `INFORME.md`)
- [ ] 📄 8. Extender el informe técnico (esqueleto en `INFORME.md`)

## 5.1 MQTT seguro (auth + TLS + ACLs)
- [x] ✅ Usuario/contraseña con `mosquitto_passwd` (`allow_anonymous false`)
- [x] ✅ Certificado TLS autofirmado + broker en **8883** (cert `CN=mosquitto` con SAN)
- [x] ✅ **Node-RED conectado con TLS** (8883) — handshake verificado (`authorized=true`)
- [x] ✅ ACLs por cliente (`acl.acl`, 5 usuarios: nodered, mkr1000, esp32_cam, predictor, coap)
- [x] ✅ Tópico `smarthome/equipo2/llm/decision` (controlador clásico + agente)
- [x] ✅ Tópico `smarthome/equipo2/llm/respuesta` — la consulta natural ahora **publica a MQTT** además del dashboard

> Matiz honesto: el broker y Node-RED hablan TLS. Los dispositivos físicos no:
> el ESP32-CAM sirve fotos por HTTP (no usa MQTT) y el MKR1000 (WiFi101) usa 1883
> plano por limitación de hardware. El broker enruta entre ambos listeners.

## 5.2 CoAP
- [x] ✅ Firmware ESP32 publica por CoAP (DHT22 → temp/humedad, UDP 5683) — `esp32/esp32_coap_sensor.ino`
- [x] ✅ Recepción de los recursos CoAP y **redirección a MQTT** — servicio `coap-bridge` (`aiocoap`)
  - *Verificado end-to-end:* `PUT coap://.../temperatura` → `MQTT smarthome/equipo2/temperatura {"valor":24.7,"fuente":"coap"}`
  - *Nota: se usó `aiocoap` en vez de `node-red-contrib-coap` porque ese nodo no carga con Node.js 20 (deja a Node-RED esperando tipos). El microservicio cumple la misma función y es más robusto.*
- [ ] 📄 Comparación tamaño/ancho de banda MQTT vs CoAP (tabla en `INFORME.md`)

## 5.3 LLM como controlador inteligente
- [x] ✅ Ollama operativo, responde JSON válido
- [x] ✅ Node-RED construye el prompt con el estado real del hogar
- [x] ✅ `POST /api/generate` con `"format":"json"`
- [x] ✅ Parsea la respuesta y publica comandos MQTT
- [x] ✅ **Comandos LED/decisión ahora van a `smarthome/equipo2/...`** (corregido el desajuste equipo1/equipo2) → llegan al dispositivo real (MKR1000)

## 5.4 Consulta en lenguaje natural
- [x] ✅ Campo de texto en el dashboard (`/ui`)
- [x] ✅ Inyecta los datos de sensores como contexto
- [x] ✅ Envía el prompt al LLM local
- [x] ✅ Muestra la respuesta en el dashboard (y la publica a `llm/respuesta`)

## 5.5 Seguridad (implementación)
- [x] ✅ Autenticación MQTT
- [x] ✅ Cifrado TLS en el transporte (8883, Node-RED conectado)
- [x] ✅ ACLs por tópico/cliente
- [ ] 📄 Análisis de vulnerabilidad + mitigación (informe)

## Entregables U2
- [x] ✅ Firmware ESP32 con TLS (CA real embebido)
- [x] ✅ Firmware ESP32 con CoAP
- [x] ✅ Flujo de Node-RED exportado en `.json`
- [x] ✅ `mosquitto.conf` + `acl.acl` + `passwd`
- [x] ✅ **Carpeta `unidad2/`** con todos los entregables agrupados (+ README)

## Rúbrica U2 (estimación)
| Criterio | Peso | Estado |
|---|---|---|
| MQTT seguro (TLS + auth) | 20% | ✅ Logrado (broker 8883 + auth + Node-RED por TLS) |
| ACLs y análisis de seguridad | 10% | ✅ ACLs · 📄 análisis (informe) |
| CoAP implementado | 15% | ✅ Logrado (firmware + puente CoAP→MQTT verificado) |
| LLM local (Ollama) | 25% | ✅ Logrado (responde JSON y publica a equipo2) |
| Consulta en lenguaje natural | 15% | ✅ Logrado |
| Informe técnico | 10% | 📄 Pendiente (esqueleto listo) |
| Defensa oral | 5% | — |

**Plus implementado (no exigido explícito):** "Persona detectada por cámara" — flujo
ESP32-CAM `/capture` → `api-ia /recognize` → `gemelo.persona` (pestaña "Camara -> Persona").

---

# UNIDAD 3 — Gemelo Digital y Agente Autónomo

## Objetivos específicos
- [x] ✅ 1. Stack completo con Docker Compose (9 servicios)
- [x] ✅ 2. Gemelo digital JSON sincronizado en tiempo real (sobre TLS)
- [x] ✅ 3. Gemelo expuesto por API REST (`GET /gemelo/estado`)
- [x] ✅ 4. Script de predicción a 30 min (`numpy.polyfit`) — co2 y distancia
- [x] ✅ 5. Agente autónomo en n8n con acciones en cadena
- [x] ✅ 6. Dashboard en Grafana (histórico, predicción, log del agente, alerta)
- [ ] 📄 7. Análisis de escalabilidad industrial (informe)
- [ ] 📄 8. Informe técnico consolidado

## 5.1 Stack Docker Compose
- [x] ✅ `docker compose up -d` levanta todo — 9 contenedores: mosquitto, nodered, ollama, influxdb, grafana, n8n, predictor, api-ia, **coap-bridge**
- [x] ✅ Servicios comunicados entre sí (verificado en vivo)

## 5.2 Gemelo Digital
- [x] ✅ Sincronizado con MQTT (TLS) en tiempo real
- [x] ✅ Historial de 60 registros (`historial_1h`)
- [x] ✅ API REST `GET /gemelo/estado`
- [x] ✅ Campo `resumen_llm`
- [x] ✅ Robustez: un error transitorio ya no resetea el gemelo (nodo catch aislado)

## 5.3 Predicción de series de tiempo
- [x] ✅ Script Python periódico (`unidad3/predictor/predict.py`)
- [x] ✅ Consulta 6h desde InfluxDB
- [x] ✅ Regresión lineal `numpy.polyfit`
- [x] ✅ Publica a MQTT (`prediccion/co2`, `prediccion/distancia`) — llega al gemelo por TLS (verificado)
- [x] ✅ Alerta preventiva (`"tipo":"preventiva"`)
- [x] ✅ Visualización en Grafana (real vs proyección)

## 5.4 Agente Autónomo (n8n + Ollama)
- [x] ✅ Trigger por timer (cada 2 min), workflow activo
- [x] ✅ Obtiene contexto desde la API REST del gemelo
- [x] ✅ Razona con el LLM (prompt de agente + herramientas)
- [x] ✅ Ejecuta acciones en cadena (actuadores vía `/agente/accion` → MQTT equipo2)
- [x] ✅ Registra razonamiento + acciones en InfluxDB (measurement `agente`)

## 5.5 Dashboard Grafana
- [x] ✅ Series de tiempo (co2, distancia, sonido)
- [x] ✅ Predicción (real + proyección 30 min)
- [x] ✅ Log de decisiones del agente
- [x] ✅ Estado actual (co2 con umbrales)
- [x] ✅ Alerta "CO2 alto (>400 ppm)" con webhook → Node-RED (`noDataState: OK`, sin falsos positivos)

## 5.6 Análisis de aplicación industrial
- [ ] 📄 Diagrama + protocolos + escalabilidad (informe)

## Entregables U3
- [x] ✅ `docker-compose.yml` funcional (validado)
- [x] ✅ Script Python de predicción
- [x] ✅ Flujo n8n del agente (`unidad3/n8n/agente-autonomo.json`)
- [x] ✅ Dashboard Grafana (`unidad3/grafana/dashboards/smarthome-u3.json`)
- [x] ✅ Flujo Node-RED (`node-red-data/flows.json`)
- [x] ✅ Carpeta `unidad3/` (predictor, n8n, grafana, coap-bridge)

## Rúbrica U3 (estimación)
| Criterio | Peso | Estado |
|---|---|---|
| Stack Docker Compose | 15% | ✅ Logrado |
| Gemelo digital | 20% | ✅ Logrado |
| Predicción de series de tiempo | 15% | ✅ Logrado |
| Agente autónomo (n8n + LLM) | 25% | ✅ Logrado |
| Dashboard Grafana | 10% | ✅ Logrado |
| Análisis industrial | 10% | 📄 Pendiente (informe) |
| Informe y defensa final | 5% | 📄 Pendiente |

---

# Resumen ejecutivo

| Unidad | Implementación (código/infra) | Documentación (informe) |
|---|---|---|
| **2** | ✅ Completa y verificada (TLS, CoAP→MQTT, LLM, consulta NL, ACLs) | 📄 Esqueleto en `INFORME.md` |
| **3** | ✅ Completa y verificada (gemelo, predicción, Grafana+alerta, agente n8n) | 📄 Esqueleto en `INFORME.md` |

**Lo único que queda es DOCUMENTACIÓN (el informe técnico):**
1. 📄 Redactar `INFORME.md` (secciones ya estructuradas) con capturas y datos reales.
2. 📄 Análisis de la vulnerabilidad (U2) y del contexto industrial (U3).

Toda la parte técnica/funcional de Unidad 2 y 3 está implementada y probada en vivo.
