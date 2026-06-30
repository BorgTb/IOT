# Guía de pruebas / demo — SmartHome IoT (Unidad 2 y 3)

## 0. Levantar todo y verificar

```bash
docker compose up -d
docker ps --format "{{.Names}}: {{.Status}}"
```
Deben aparecer arriba: `mosquitto, nodered, ollama, influxdb, grafana, n8n, predictor, api-ia`.

### Accesos (navegador)
| Servicio | URL | Login |
|---|---|---|
| Node-RED (editor) | http://localhost:1880 | - |
| Dashboard / Chat LLM | http://localhost:1880/ui | - |
| API Gemelo Digital | http://localhost:1880/gemelo/estado | - |
| Grafana | http://localhost:3000 | admin / admin |
| n8n (agente) | http://localhost:5678 | - |
| InfluxDB | http://localhost:8086 | admin / admin123 |

---

## 1. (U2) Datos de sensores → Gemelo Digital

Publicar un dato de sensor simulado:
```bash
docker exec mosquitto mosquitto_pub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t smarthome/equipo2/alerta -m '{"distancia": 45.3, "gas": 512, "sonido": 77}'
```
Ver el gemelo actualizado:
```bash
curl -s http://localhost:1880/gemelo/estado
```
✅ Debe reflejar `gas`, `distancia`, `sonido` y crecer el `historial_1h`.
*(Si tienes el MKR1000 real encendido, los valores cambian solos cada 2s.)*

---

## 2. (U2) Chat en lenguaje natural

1. Abre http://localhost:1880/ui
2. En **"Pregunta al sistema"** escribe, por ej.:
   - `Resume el estado del hogar en una frase`
   - `¿Es seguro con estos niveles de gas?`
3. La respuesta del LLM (Ollama, `qwen2.5:0.5b`) aparece abajo, usando los valores reales del gemelo.

---

## 3. (U2) Controlador LLM automático

Forzar una condición crítica (gas alto) para que el LLM decida:
```bash
docker exec mosquitto mosquitto_pub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t smarthome/equipo2/alerta -m '{"gas": 520, "distancia": 50, "sonido": 40}'
```
Observar los comandos de actuador (en otra terminal):
```bash
docker exec mosquitto mosquitto_sub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t 'smarthome/equipo2/control/#' -v
```
✅ Si el LLM decide, verás `smarthome/equipo2/control/led ON`.

Para ver la **decisión completa** (`llm/decision` con razonamiento): abre el editor
http://localhost:1880 → pestaña **"Gemelo Digital + LLM"** → panel **debug** (barra derecha).
*(El usuario `mkr1000` solo puede leer `control/#`; los tópicos `llm/#` se ven mejor en el debug de Node-RED.)*

---

## 4. (U3) InfluxDB recibe los sensores

```bash
docker exec influxdb influx query \
 'from(bucket:"sensores")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="sensor")|>last()' \
 --org smarthome --token smarthome_token_2024
```
✅ Devuelve filas para `gas`, `distancia`, `sonido`.

---

## 5. (U3) Predictor

```bash
docker logs --tail 10 predictor
```
✅ Líneas tipo `Prediccion gas 30min: 124.6 ppm ...`.

La predicción llega al gemelo:
```bash
curl -s http://localhost:1880/gemelo/estado
```
✅ Campo `prediccion_30min.gas` con un número.

---

## 6. (U3) Grafana

1. Abre http://localhost:3000 (admin/admin) → dashboard **"SmartHome IoT - Unidad 3"**.
2. Paneles: Gas real vs predicción, Gas actual, Distancia/Sonido, Log del agente.
3. Alerta: **Alerting → Alert rules** → debe estar **"Gas alto (>400 ppm)"**.

Probar el webhook de la alerta manualmente:
```bash
curl -s -X POST http://localhost:1880/grafana/alerta -H "Content-Type: application/json" \
  -d '{"status":"firing","alerts":[{"labels":{"alertname":"Gas alto"}}]}' -w "\nHTTP %{http_code}\n"
```
✅ HTTP 200, y la alerta queda en `gemelo.alertas_activas`.

---

## 7. (U3) Agente autónomo (n8n)

El agente corre solo cada 2 minutos. Para verlo:
1. Abre http://localhost:5678 → workflow **"Agente IoT Autonomo"** → pestaña **Executions**.
2. O revisa su log en InfluxDB:
```bash
docker exec influxdb influx query \
 'from(bucket:"sensores")|>range(start:-15m)|>filter(fn:(r)=>r._measurement=="agente")|>last()' \
 --org smarthome --token smarthome_token_2024
```
✅ Muestra `razonamiento`, `acciones`, `num`.

### Demo: forzar al agente a actuar
1. Publica gas crítico:
```bash
docker exec mosquitto mosquitto_pub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t smarthome/equipo2/alerta -m '{"gas": 600, "distancia": 50, "sonido": 40}'
```
2. (opcional) Escucha los actuadores:
```bash
docker exec mosquitto mosquitto_sub -h localhost -p 1883 -u mkr1000 -P mkr1000_iot \
  -t 'smarthome/equipo2/control/#' -v
```
3. Espera el ciclo del agente (hasta 2 min). Si decide encender LED/buzzer, lo verás en `control/led`.

### Probar directamente la ejecución de acción en cadena
```bash
curl -s -X POST http://localhost:1880/agente/accion -H "Content-Type: application/json" \
  -d '{"dispositivo":"led","estado":true}'
```
✅ Responde `{"ok":true,...}` y publica `smarthome/equipo2/control/led ON`.
