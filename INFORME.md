# Informe Técnico — SmartHome IoT (Unidades 1, 2 y 3)

> Plantilla con todas las secciones que exige el PDF. Rellenar los bloques `>` con
> redacción, capturas y datos reales. Las partes técnicas ya están resueltas en el
> código (ver `README.md`, `CHECKLIST.md`, `PRUEBAS.md`).

**Equipo:** equipo2
**Fecha:** _____
**Integrantes:** _____

---

# UNIDAD 2

## 1. Configuración de MQTT seguro (TLS + auth + ACLs)
> Describir el proceso. Datos ya implementados que puedes citar:
> - `mosquitto.conf`: listeners 1883 y **8883 (TLS, tlsv1.2)**, `allow_anonymous false`.
> - Auth con `mosquitto_passwd` (4 usuarios: nodered, mkr1000, esp32_cam, predictor).
> - CA autofirmada `SmartHomeCA`; cert del broker `CN=mosquitto` con SAN
>   (`DNS:mosquitto, localhost, IP:127.0.0.1`). Comando de generación en `unidad2/README.md`.
> - Node-RED conecta al broker por **8883 con TLS** validando el CA (`/certs/ca.crt`).
> - ACLs por cliente (`acl.acl`): cada usuario solo accede a sus tópicos.
> Incluir captura de Node-RED "Connected" sobre el broker 8883.

## 2. Comparativa MQTT vs. CoAP
> Tabla a completar midiendo el mismo dato (ej. temperatura) por ambos protocolos:

| Métrica | MQTT (TCP/8883) | CoAP (UDP/5683) |
|---|---|---|
| Transporte | TCP (orientado a conexión) | UDP (sin conexión) |
| Tamaño aprox. del mensaje | _____ bytes | _____ bytes |
| Overhead de cabecera | ~ por la sesión TCP+TLS | mínimo (4 bytes header) |
| Confiabilidad | alta (QoS) | best-effort (CON/NON) |
| Caso de uso | continuo, crítico | sensores batería/bajo BW |

> El puente CoAP→MQTT está en la pestaña "CoAP + Camara" de Node-RED
> (`node-red-contrib-coap`, servidor en UDP 5683, recursos `/temperatura` y `/humedad`).

## 3. Arquitectura de integración del LLM
> - Diagrama: Sensores → MQTT → Node-RED (construye prompt) → Ollama → Node-RED publica MQTT.
> - **Prompt utilizado** (copiar del nodo "Construir Prompt LLM" de `flows.json`).
> - Modelo: `qwen2.5:0.5b` vía `POST /api/generate` con `"format":"json"`.
> - Ejemplos de respuestas JSON del modelo (capturar del debug de Node-RED).

## 4. Análisis de seguridad (vulnerabilidad + mitigación)
> Elegir y desarrollar al menos una. Candidatas reales de este stack:
> - **MQTT sin TLS / broker expuesto:** mitigado con TLS 8883 + auth + ACLs.
> - **Endpoints HTTP sin autenticación** (`/agente/accion`, `/grafana/alerta`):
>   cualquiera en la LAN podría accionar actuadores → mitigación: token/API key o red aislada.
> - **Secretos en texto plano** (token InfluxDB, passwords MQTT) → mitigación: variables
>   de entorno / secrets de Docker.
> - **CA autofirmada / firmware sin actualización segura** (OTA firmado).

## 5. Capturas del dashboard (consulta en lenguaje natural)
> Captura de http://localhost:1880/ui con una pregunta y la respuesta del LLM.

## 6. Problemas en la integración del LLM y cómo se resolvieron
> Ejemplos reales documentables:
> - Bug `payload` vs `msg.payload` en los nodos function → el gemelo se reseteaba en cada
>   mensaje y el chat respondía valores por defecto. Solución: usar `msg.payload`.
> - Nodo `catch` que reseteaba todo el gemelo ante cualquier error → aislado con un nodo
>   intermedio que preserva el estado.
> - Modelo `qwen2.5:0.5b` a veces mezcla idiomas; mitigado forzando `format:json`.

## 7. Reflexión crítica: LLM vs. regla clásica
> ¿Cuándo conviene el LLM (contexto ambiguo, lenguaje natural) y cuándo una regla if/else
> (latencia, determinismo, seguridad crítica)?

---

# UNIDAD 3

## 1. Arquitectura del stack Docker Compose
> Diagrama de servicios y red (`red_iot`, subred 10.5.0.0/16). Ver diagrama en `README.md`.
> Servicios: mosquitto, nodered, ollama, influxdb, grafana, n8n, predictor, api-ia.

## 2. Diseño e implementación del gemelo digital
> - Objeto JSON global en Node-RED, sincronizado con MQTT.
> - Historial de 60 registros (`historial_1h`).
> - API REST `GET /gemelo/estado`. Campo `resumen_llm`.
> - Estructura del JSON (copiar una respuesta real del endpoint).

## 3. Script de predicción (método + gráficos)
> - `numpy.polyfit` grado 1 sobre los últimos 20 valores; proyección a 30 min.
> - Lee 6h de InfluxDB (measurement `sensor`), publica a MQTT y a InfluxDB (`prediccion`).
> - Gráfico Grafana: real vs. proyección superpuesta (capturar panel).

## 4. Diseño del agente autónomo (n8n)
> - Prompt de agente + herramientas (`activar_actuador`, `enviar_notificacion`, `registrar_evento`).
> - Flujo: Timer 2 min → GET gemelo → Ollama → parsear acciones → ejecutar → log InfluxDB.
> - **Ejemplo real de decisión** tomada durante las pruebas (copiar del measurement `agente`).

## 5. Dashboard Grafana (capturas)
> Capturas del dashboard "SmartHome IoT - Unidad 3": gas real vs predicción, distancia/sonido,
> log del agente, estado actual, y la regla de alerta "Gas alto (>400 ppm)".

## 6. Análisis del contexto industrial elegido
> Elegir uno (sala de servidores / agricultura / microrred / edificio inteligente):
> diagrama de arquitectura adaptada, protocolos a esa escala, desafíos de escalabilidad,
> y valor del agente LLM en ese entorno.

## 7. Reflexión crítica: limitaciones del LLM como controlador IoT
> Latencia, no-determinismo, fallos de parseo JSON; cuándo preferir una regla clásica.

## 8. Conclusiones generales del proyecto integrador
> Cierre.
