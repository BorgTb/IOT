# Plan de Implementación — SmartHome IoT (Unidades 2 y 3)

## Priorización por ponderación (qué rinde más nota)

| Prioridad | Componente | Peso | Unidad |
|-----------|-----------|------|--------|
| 🔴 1 | Agente autónomo (n8n + LLM) | 25% | U3 |
| 🔴 2 | LLM local (Ollama + Node-RED) | 25% | U2 |
| 🟡 3 | Gemelo digital + API REST | 20% | U3 |
| 🟡 4 | MQTT seguro (TLS + auth + ACLs) | 20% | U2 |
| 🟢 5 | Consulta lenguaje natural (Dashboard) | 15% | U2 |
| 🟢 6 | CoAP en nodo sensor | 15% | U2 |
| 🟢 7 | Predicción series de tiempo | 15% | U3 |
| 🔵 8 | Stack Docker Compose completo | 15% | U3 |
| 🔵 9 | Dashboard Grafana | 10% | U3 |
| 🔵 10 | Análisis industrial | 10% | U3 |
| ⚪ 11 | Informe + Defensa | 15% | U2+U3 |

---

## Fase 0: Preparación y Baseline (Día 1)

**Objetivo:** Asegurar que el sistema actual funciona antes de modificarlo.

- [ ] **0.1** Hacer backup de `flows.json`, `mosquitto.conf`, y firmware ESP32 actual
- [ ] **0.2** Verificar que `docker-compose up -d` levanta los 3 servicios actuales sin errores
- [ ] **0.3** Probar que el test sensor simulado (`test/test.py`) genera datos y llegan a Node-RED
- [ ] **0.4** Probar que el ciclo cámara → `/recognize` → MQTT funciona
- [ ] **0.5** Verificar que la DB SQLite (`data_general`) tiene datos históricos para la predicción

---

## Fase 1: MQTT Seguro (TLS + Auth + ACLs) — Peso 20% U2 (Días 2-3)

**Dependencia:** Fase 0 completa. **Afecta a:** Node-RED, ESP32, test script.

### 1.1 Generar infraestructura PKI
- [ ] Crear carpeta `mosquitto/certs/`
- [ ] Generar CA autofirmada:
  ```
  openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt
  ```
- [ ] Generar certificado del broker:
  ```
  openssl req -new -keyout broker.key -out broker.csr
  openssl x509 -req -days 365 -CA ca.crt -CAkey ca.key -CAcreateserial -in broker.csr -out broker.crt
  ```

### 1.2 Configurar autenticación y ACLs
- [ ] Crear `mosquitto/config/passwd` con `mosquitto_passwd`:
  - Usuario `nodered` (acceso a todos los tópicos `smarthome/equipo1/#`)
  - Usuario `esp32_cam` (solo publish/subscribe a `smarthome/equipo1/camara/#`)
  - Usuario `mkr1000` (solo publish a `smarthome/equipo2/alerta`)
  - Usuario `predictor` (solo publish a `smarthome/equipo2/prediccion/#`)
- [ ] Crear `mosquitto/config/acl.acl`:
  ```
  user nodered
  topic readwrite smarthome/equipo1/#
  topic readwrite smarthome/equipo2/#

  user esp32_cam
  topic readwrite smarthome/equipo1/camara/#

  user mkr1000
  topic write smarthome/equipo2/alerta

  user predictor
  topic write smarthome/equipo2/prediccion/#
  ```

### 1.3 Actualizar `mosquitto.conf`
- [ ] Agregar al archivo existente:
  ```
  listener 8883
  certfile /mosquitto/config/certs/broker.crt
  keyfile /mosquitto/config/certs/broker.key
  cafile /mosquitto/config/certs/ca.crt
  tls_version tlsv1.2

  password_file /mosquitto/config/passwd
  acl_file /mosquitto/config/acl.acl
  allow_anonymous false
  ```

### 1.4 Actualizar Node-RED
- [ ] Configurar nodo MQTT broker con:
  - Host: `mosquitto` (o `172.20.10.3`)
  - Puerto: `8883`
  - TLS: habilitar, pegar CA certificate
  - Usuario: `nodered`, contraseña correspondiente
- [ ] Verificar que los flujos existentes usen el nuevo broker TLS

### 1.5 Actualizar ESP32-CAM firmware
- [ ] Agregar librería `WiFiClientSecure` al sketch
- [ ] Agregar certificado CA como constante string
- [ ] Cambiar conexión MQTT a puerto 8883 con TLS
- [ ] Configurar credenciales `esp32_cam`
- [ ] **Verificación:** Publicar un mensaje de prueba y confirmar que Node-RED lo recibe

### 1.6 Actualizar test script
- [ ] Agregar TLS y credenciales a `test/test.py`
- [ ] Verificar que el script publica correctamente al broker seguro

### ✅ Verificación Fase 1
- [ ] `mosquitto_sub -h localhost -p 8883 --cafile ca.crt -u nodered -t "#" -v` muestra todos los mensajes
- [ ] `mosquitto_sub -h localhost -p 1883 -t "#"` (sin auth) **falla** (anon deshabilitado)
- [ ] Cliente `esp32_cam` NO puede publicar en `smarthome/equipo2/alerta` (ACL deniega)
- [ ] Node-RED recibe datos del ESP32 y del test script correctamente

---

## Fase 2: CoAP en Nodo Sensor — Peso 15% U2 (Días 4-5)

**Dependencia:** Independiente de Fase 1. Se puede hacer en paralelo.

### 2.1 Lado ESP32 (nodo sensor CoAP)
- [ ] Sketch con lectura de sensor DHT22 (temperatura/humedad)
- [ ] Librería `CoAP-simple-library`
- [ ] Publicar recurso CoAP en `coap://[ip]/temperatura` y `coap://[ip]/humedad`
- [ ] Intervalo: 30 segundos
- [ ] Alternativa: simulador CoAP en Python con `aiocoap` si no hay HW extra

### 2.2 Lado Node-RED
- [ ] Instalar `node-red-contrib-coap`
- [ ] Crear flujo: nodo CoAP in → function (transformar) → MQTT out (`smarthome/equipo1/coap/temperatura`)

### 2.3 Comparativa MQTT vs CoAP (para el informe)
- [ ] Medir tamaño de payload MQTT vs CoAP para el mismo dato
- [ ] Medir latencia (round-trip) con Wireshark o logs
- [ ] Medir número de paquetes intercambiados (MQTT: TCP SYN+ACK+PUB, CoAP: UDP single datagram)
- [ ] Documentar resultados en tabla

### ✅ Verificación Fase 2
- [ ] Datos CoAP aparecen en Node-RED debug
- [ ] Datos se re-publican a MQTT correctamente
- [ ] Dashboard muestra datos del sensor CoAP

---

## Fase 3: Ollama + LLM Local — Peso 25% U2 + base para 25% U3 (Días 5-7)

**Dependencia:** Fase 0 (no requiere Fase 1 para desarrollarse).

### 3.1 Instalación de Ollama
- [ ] Descargar Ollama para Windows desde `https://ollama.com/download`
- [ ] `ollama pull qwen2.5:0.5b` (0.8 GB) — modelo liviano Qwen 0.8B parámetros
- [ ] Verificar: `ollama run qwen2.5:0.5b "Hola, responde en una línea"` → funciona
- [ ] Asegurar que `ollama serve` corre en segundo plano (servicio Windows)

### 3.2 Verificar conectividad Node-RED → Ollama
- [ ] Desde Node-RED: nodo HTTP Request → `http://host.docker.internal:11434/api/generate`
- [ ] Probar prompt simple con `"stream": false, "format": "json"`
- [ ] Verificar que la respuesta llega y es parseable

### 3.3 Integrar LLM como reemplazo de reglas if/else (U2)
- [ ] Crear flujo en Node-RED:
  ```
  MQTT in (smarthome/equipo2/alerta)
    → Function: construir_prompt_contexto()
    → HTTP Request (POST Ollama /api/generate)
    → Function: parsear_respuesta_llm()
      → Output 1: MQTT out (smarthome/equipo1/control/led)
      → Output 2: MQTT out (smarthome/equipo1/llm/decision)
      → Output 3: Dashboard UI text (alerta)
  ```
- [ ] El prompt debe seguir la estructura del requerimiento sección 5.3
- [ ] Parsear JSON de respuesta y publicar comandos MQTT

### ✅ Verificación Fase 3
- [ ] Enviar sensor data con gas > 400 → LLM responde con `nivel_alerta: "critico"`
- [ ] Enviar sensor data normal → LLM responde `nivel_alerta: "normal"`
- [ ] Comando MQTT `control/led` se publica correctamente según decisión del LLM
- [ ] El LED físico (o simulado) responde al comando

---

## Fase 4: Gemelo Digital + Consulta Natural — Peso 20% + 15% U2/U3 (Días 7-9)

**Dependencia:** Fase 3 (gemelo alimenta al LLM).

### 4.1 Implementar Gemelo Digital en Node-RED
- [ ] Crear flujo de almacenamiento:
  - `MQTT in (#)` → Function actualizar gemelo
  - Usar `flowContext` o `globalContext` para el JSON del gemelo
  - Mantener array rotatorio de últimos 60 registros (timestamp, temperatura, gas, distancia, sonido)
  - Campos: `ultimo_update`, `estado_actual`, `historial_1h`, `alertas_activas`, `prediccion_30min`, `resumen_llm`
- [ ] Exponer API REST: nodo HTTP in `GET /gemelo/estado` → devuelve gemelo JSON
- [ ] Probar: `curl http://localhost:1880/gemelo/estado` devuelve JSON completo

### 4.2 Interfaz de Consulta Natural (Dashboard U2)
- [ ] Agregar al dashboard Node-RED:
  - `ui-text-input` para la pregunta del usuario
  - `ui-button` para enviar
  - `ui-template` o `ui-text` para mostrar la respuesta
- [ ] Flujo: button click → Function (tomar pregunta + gemelo actual como contexto) → HTTP Request Ollama → Function (parsear) → mostrar respuesta
- [ ] Probar preguntas del requerimiento:
  - "¿Es seguro dormir con estos niveles de gas?"
  - "Resume el estado del hogar en una frase."
  - "¿Qué condición del hogar es más preocupante ahora mismo?"

### ✅ Verificación Fase 4
- [ ] `GET /gemelo/estado` responde con JSON actualizado
- [ ] Dashboard muestra respuestas coherentes al estado actual
- [ ] El historial_1h contiene al menos 60 entradas después de 1 hora de ejecución

---

## Fase 5: Stack Docker Completo (InfluxDB + Grafana + n8n) — Peso 15% U3 (Días 8-10)

**Dependencia:** Fase 1 (MQTT seguro debe funcionar).

### 5.1 Actualizar `docker-compose.yml`
- [ ] Agregar servicios manteniendo los existentes:
  ```yaml
  influxdb:
    image: influxdb:2.7
    ports: ["8086:8086"]
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_ORG: smarthome
      DOCKER_INFLUXDB_INIT_BUCKET: sensores
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: <token>
    volumes: ["./influxdb-data:/var/lib/influxdb2"]
    networks: [red_iot]
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    depends_on: [influxdb]
    volumes: ["./grafana-data:/var/lib/grafana"]
    networks: [red_iot]
  n8n:
    image: n8nio/n8n:latest
    ports: ["5678:5678"]
    environment:
      N8N_SECURE_COOKIE: "false"
    volumes: ["./n8n-data:/home/node/.n8n"]
    networks: [red_iot]
  ```
- [ ] Agregar todos los servicios a la red `red_iot`
- [ ] Verificar MTU 1350 para todos los contenedores

### 5.2 Migrar datos de SQLite a InfluxDB
- [ ] Crear flujo Node-RED que lee SQLite y envía a InfluxDB vía HTTP API

### ✅ Verificación Fase 5
- [ ] `docker compose up -d` levanta los 6 servicios sin errores
- [ ] `docker compose ps` muestra todos como "Up"
- [ ] InfluxDB UI en `http://localhost:8086` accesible
- [ ] Grafana en `http://localhost:3000` accesible
- [ ] n8n en `http://localhost:5678` accesible
- [ ] Los contenedores se comunican entre sí por nombre de servicio

---

## Fase 6: Predicción de Series de Tiempo — Peso 15% U3 (Días 10-12)

**Dependencia:** Fase 5 (InfluxDB con datos históricos).

### 6.1 Script de predicción Python
- [ ] Crear `unidad3/predictor/predict.py`:
  - Consultar últimos 6h desde InfluxDB vía API
  - Implementar regresión lineal con `numpy.polyfit` sobre últimos 20 valores
  - Proyectar temperatura y gas a 30 minutos
  - Publicar resultados en MQTT (broker seguro, usuario `predictor`)
  - Si proyección supera umbral → publicar alerta preventiva
- [ ] Dockerizar: crear `unidad3/predictor/Dockerfile` (python:3.11-slim + paho-mqtt + numpy + influxdb-client)
- [ ] Agregar al `docker-compose.yml` como servicio `predictor`

### ✅ Verificación Fase 6
- [ ] Predicciones llegan a MQTT cada 10 minutos
- [ ] Alerta preventiva se dispara si proyección > umbral
- [ ] Datos de predicción se almacenan en InfluxDB para Grafana

---

## Fase 7: Agente Autónomo (n8n + Ollama) — Peso 25% U3 (Días 11-14)

**Dependencia:** Fase 3 (Ollama), Fase 4 (Gemelo Digital API), Fase 5 (n8n funcionando).

### 7.1 Configurar flujo n8n
- [ ] Workflow "Agente SmartHome":
  - **Trigger 1:** Schedule (cada 5 minutos)
  - **Trigger 2:** Webhook (desde Node-RED ante evento crítico)
  - **Step 1:** HTTP Request → `GET http://nodered:1880/gemelo/estado`
  - **Step 2:** HTTP Request → `POST http://host.docker.internal:11434/api/generate` con prompt de agente
  - **Step 3:** Code (JavaScript) → parsear respuesta JSON del LLM
  - **Step 4:** Iterar sobre `acciones[]` y ejecutar:
    - `activar_actuador` → MQTT out
    - `enviar_notificacion` → HTTP Request (Telegram API)
    - `registrar_evento` → HTTP Request (InfluxDB API)
    - `ajustar_umbral` → Node-RED webhook o MQTT
  - **Step 5:** Escribir log de decisión en InfluxDB

### 7.2 Prompt del agente (sección 5.4 del requerimiento)
- [ ] Implementar exactamente el prompt especificado con herramientas: `activar_actuador`, `enviar_notificacion`, `registrar_evento`, `ajustar_umbral`
- [ ] Probar que el LLM devuelve array de acciones en el formato correcto

### 7.3 Mapear acciones a ejecución real
- [ ] `activar_actuador(dispositivo, estado)` → publicar MQTT en `smarthome/equipo1/control/<dispositivo>`
- [ ] `enviar_notificacion(mensaje)` → llamar API de Telegram Bot
- [ ] `registrar_evento(descripcion)` → POST a InfluxDB write API
- [ ] `ajustar_umbral(sensor, nuevo_umbral)` → publicar MQTT en `smarthome/equipo2/config/<sensor>`

### ✅ Verificación Fase 7
- [ ] n8n se activa cada 5 minutos y consulta gemelo digital
- [ ] LLM responde con acciones relevantes al estado actual
- [ ] Actuador LED se activa/desactiva según decisión del agente
- [ ] Notificación Telegram se envía cuando corresponde
- [ ] Log de decisiones se escribe en InfluxDB

---

## Fase 8: Dashboard Grafana — Peso 10% U3 (Días 13-15)

**Dependencia:** Fase 5 (InfluxDB+Grafana), Fase 6 (predicción), Fase 7 (log agente).

### 8.1 Configurar datasource
- [ ] En Grafana UI: Add datasource → InfluxDB
- [ ] URL: `http://influxdb:8086`
- [ ] Organization: `smarthome`, Token: `<token>`, Bucket: `sensores`

### 8.2 Paneles requeridos
- [ ] **Panel 1:** Series de tiempo — temperatura, humedad y gas (últimas 6 horas)
- [ ] **Panel 2:** Predicción — valor real + proyección 30min superpuesta
- [ ] **Panel 3:** Log del agente — tabla con timestamp, razonamiento y acciones
- [ ] **Panel 4:** Estado del gemelo digital — tabla/stat con últimos valores de cada variable

### 8.3 Alerta en Grafana
- [ ] Configurar alerta: si `temperatura` > 35°C o `gas` > 400 ppm → notificación
- [ ] Canal de notificación: webhook a Node-RED (que reenvía a Telegram) o email

### ✅ Verificación Fase 8
- [ ] Dashboard Grafana exportable como JSON guardado en `unidad3/grafana-dashboard.json`
- [ ] Todos los paneles muestran datos actualizados
- [ ] Alerta configurada y disparándose correctamente

---

## Fase 9: Análisis Industrial — Peso 10% U3 (Días 15-16)

**Dependencia:** Sistema completo funcionando.

- [ ] Elegir contexto industrial (ej: sala de servidores, agricultura, edificio inteligente)
- [ ] Crear diagrama de arquitectura adaptada
- [ ] Analizar:
  - Protocolos recomendados a escala industrial
  - Desafíos de escalabilidad (núm. dispositivos, ancho de banda, latencia)
  - Cómo el agente LLM aporta valor operacional

---

## Fase 10: Informe Técnico Consolidado — Peso 10% + 5% U2/U3 (Días 16-18)

- [ ] Consolidar informe de Unidad 1 + 2 + 3 (20-30 páginas)
- [ ] Incluir:
  - Diagrama de arquitectura Docker Compose
  - Configuración MQTT seguro (TLS + auth + ACLs) con capturas
  - Comparativa MQTT vs CoAP (tamaño, latencia, paquetes)
  - Arquitectura de integración LLM + prompt utilizado + ejemplos
  - Diseño del gemelo digital (estructura JSON, API REST)
  - Script de predicción con gráficos
  - Agente autónomo: prompt, herramientas, decisiones reales de pruebas
  - Dashboard Grafana con capturas
  - Análisis de seguridad: vulnerabilidad identificada + mitigación
  - Análisis de contexto industrial
  - Reflexión crítica: ¿cuándo el LLM es mejor que reglas clásicas?
  - Problemas encontrados y soluciones

---

## Diagrama de Dependencias

```
Fase 0 (Baseline)
  ├──> Fase 1 (MQTT Seguro) ──> Fase 5 (Docker Stack)
  ├──> Fase 2 (CoAP) [paralelo]
  ├──> Fase 3 (Ollama) ──> Fase 4 (Gemelo + Consulta)
  │                       └──> Fase 7 (Agente n8n) ──> Fase 8 (Grafana)
  └──> Fase 5 ──> Fase 6 (Predicción) ──> Fase 8

Todas ──> Fase 9 (Análisis Industrial) ──> Fase 10 (Informe)
```

---

## Gestión de Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| ESP32 no tiene suficiente memoria para TLS | Media | Alto | Usar certificado CA solamente (no client cert); probar con PSRAM habilitado |
| Ollama no corre en Windows estable | Baja | Alto | Alternativa: ejecutar Ollama en contenedor Docker Linux |
| n8n no puede conectarse a Ollama | Media | Alto | Usar `host.docker.internal`; en Linux probar `172.17.0.1` |
| Modelo Qwen 2.5 0.5B lento en CPU | Media | Bajo | Modelo ya es muy pequeño (0.8 GB); funciona bien en CPU |
| InfluxDB consume muchos recursos | Media | Bajo | Usar SQLite como fallback; InfluxDB es solo para visualización |
| Parseo de JSON del LLM falla | Alta | Medio | Validar con schema; reintentar si falla; tener respuesta por defecto |
