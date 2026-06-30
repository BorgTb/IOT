# Unidad 2 — Entregables

Copia consolidada de los entregables de la Unidad 2 (protocolos seguros + LLM local).
Los archivos en producción viven en la raíz del repo; aquí están agrupados según pide el PDF.

## Contenido

```
unidad2/
├── firmware/
│   ├── esp32_mqtt_tls.ino     # ESP32-CAM con MQTT sobre TLS (puerto 8883)
│   ├── esp32_coap_sensor.ino  # Nodo sensor ESP32 + DHT22 publicando por CoAP (UDP 5683)
│   └── ProyectoIOT.ino        # MKR1000: sensores (gas, sonido, distancia) por MQTT
├── flows.json                 # Flujo Node-RED (gemelo, LLM, consulta natural, CoAP, TLS)
└── mosquitto/
    ├── mosquitto.conf         # Listeners 1883 + 8883 TLS, auth y ACL
    ├── acl.acl                # Permisos por usuario/tópico
    ├── passwd                 # Usuarios (hash con mosquitto_passwd)
    └── certs/
        ├── ca.crt             # CA autofirmada (SmartHomeCA)
        └── broker.crt         # Certificado del broker (CN=mosquitto, con SAN)
```

## Funcionalidades implementadas (5.x del PDF)

| # | Requisito | Estado |
|---|---|---|
| 5.1 | MQTT con auth (`mosquitto_passwd`) | ✅ |
| 5.1 | TLS autofirmado en puerto 8883 | ✅ |
| 5.1 | Node-RED conectado por TLS (8883) | ✅ |
| 5.1 | ACLs por cliente | ✅ |
| 5.1 | Tópicos `llm/decision` y `llm/respuesta` | ✅ |
| 5.2 | ESP32 publica por CoAP | ✅ (firmware) |
| 5.2 | Node-RED recibe CoAP y redirige a MQTT | ✅ (`node-red-contrib-coap`) |
| 5.3 | LLM (Ollama) como controlador, publica comandos MQTT | ✅ |
| 5.4 | Consulta en lenguaje natural en el dashboard | ✅ |
| 5.5 | Seguridad: auth + TLS + ACLs | ✅ |

## Generación del certificado (referencia)

```bash
# CA autofirmada
openssl req -new -x509 -days 365 -nodes \
  -keyout ca.key -out ca.crt -subj "/CN=SmartHomeCA"

# Clave y CSR del broker
openssl genrsa -out broker.key 2048
openssl req -new -key broker.key -out broker.csr -subj "/CN=mosquitto"

# Firmar con SAN (clave para que Node-RED valide el hostname)
openssl x509 -req -in broker.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out broker.crt -days 365 \
  -extfile <(printf "subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1")
```

## Usuarios MQTT

| Usuario | Password | Uso |
|---|---|---|
| `nodered` | (interno) | Node-RED — readwrite `equipo1/#`, `equipo2/#` |
| `mkr1000` | `mkr1000_iot` | MKR1000 — sensores |
| `esp32_cam` | `esp32_cam123` | ESP32-CAM — eventos |
| `predictor` | `predictor_iot` | Predictor — predicciones/alertas |
