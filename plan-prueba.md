# Plan de Acción: Proyecto SmartHome IoT - Unidades 2 y 3

Este documento detalla la hoja de ruta para evolucionar el prototipo inicial hacia una arquitectura IoT segura, inteligente y de nivel industrial.

## Fase 1: Seguridad y Protocolos (Unidad 2)
El objetivo es migrar de una red abierta a una infraestructura segura y probar alternativas de conectividad para nodos de bajos recursos.

- [ ] **Configuración de Mosquitto Seguro:**
  - [ ] [cite_start]Generar certificado TLS autofirmado[cite: 35].
  - [ ] [cite_start]Habilitar autenticación por usuario/contraseña usando `mosquitto_passwd`[cite: 34].
  - [ ] [cite_start]Configurar el broker para escuchar en el puerto 8883[cite: 35].
  - [ ] [cite_start]Definir Listas de Control de Acceso (ACLs) para limitar qué tópicos puede leer/escribir cada cliente[cite: 37].
- [ ] **Actualización de Clientes:**
  - [ ] [cite_start]Modificar los nodos `mqtt-broker` en Node-RED para habilitar la conexión TLS con credenciales[cite: 36].
  - [ ] [cite_start]Actualizar el firmware del ESP32-CAM y los sensores (MKR1000/ESP32) para conectarse mediante MQTTS[cite: 36].
- [ ] **Implementación de CoAP:**
  - [ ] [cite_start]Configurar al menos un nodo sensor (ej. temperatura/humedad) para publicar datos por UDP en el puerto 5683 usando CoAP[cite: 44].
  - [ ] [cite_start]Integrar el nodo `node-red-contrib-coap` en el flujo actual para recibir los datos y redirigirlos al broker MQTT[cite: 45].

## Fase 2: Infraestructura en Contenedores (Unidad 3)
Dado que ya manejas despliegues con Docker, empaquetaremos todo el stack de servicios para facilitar la escalabilidad y el control.

- [ ] **Docker Compose:**
  - [ ] [cite_start]Crear el archivo `docker-compose.yml` que levante: Mosquitto, InfluxDB (v2.7), Grafana, Node-RED y n8n[cite: 173].
  - [ ] [cite_start]Configurar redes y volúmenes persistentes para cada contenedor[cite: 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208].
- [ ] **Migración de Datos:**
  - [ ] [cite_start]Transicionar el guardado histórico que actualmente tienes en SQLite hacia el nuevo contenedor de InfluxDB[cite: 173, 244].

## Fase 3: Inteligencia Artificial Local (Unidad 2 y 3)
Reemplazar la lógica de control rígida (if/else) por razonamiento contextual utilizando modelos de lenguaje.

- [ ] **Despliegue de Ollama:**
  - [ ] [cite_start]Instalar Ollama en la máquina host (fuera de Docker)[cite: 209].
  - [ ] [cite_start]Descargar un modelo liviano (`phi3:mini` o `llama3.2:3b`)[cite: 52].
- [ ] **Gemelo Digital en Node-RED:**
  - [ ] [cite_start]Crear un objeto JSON en Node-RED que almacene el estado actual y los últimos 60 registros[cite: 211, 215].
  - [ ] [cite_start]Exponer este estado mediante una API REST en el endpoint `GET /gemelo/estado`[cite: 216].
- [ ] **Interfaz Natural (Dashboard):**
  - [ ] [cite_start]Agregar un campo de entrada de texto en la interfaz actual (`ui-page`) para realizar preguntas en lenguaje natural[cite: 103].
  - [ ] [cite_start]Crear un flujo que inyecte el contexto del gemelo digital junto a la pregunta y consulte la API de Ollama[cite: 106, 107].

## Fase 4: Predicción y Agente Autónomo (Unidad 3)
Darle al sistema capacidades proactivas.

- [ ] **Predicción de Series de Tiempo:**
  - [ ] [cite_start]Escribir un script en Python que consulte InfluxDB cada 10 minutos[cite: 243, 244].
  - [ ] [cite_start]Proyectar valores de gas y temperatura a 30 minutos usando regresión lineal o Prophet[cite: 245].
  - [ ] [cite_start]Publicar alertas preventivas en MQTT si las proyecciones superan los umbrales críticos[cite: 254].
- [ ] **Agente en n8n:**
  - [ ] [cite_start]Configurar un flujo tipo cronograma (cada 5 minutos) o mediante Webhook para eventos críticos[cite: 259, 262].
  - [ ] [cite_start]Conectar n8n a la API del Gemelo Digital y enviar el contexto estructurado a Ollama[cite: 263, 264].
  - [ ] [cite_start]Configurar el parseo de JSON en n8n para que el sistema ejecute de forma autónoma las acciones decididas por el LLM (actuadores, notificaciones Telegram, registro)[cite: 287].

## Fase 5: Visualización y Documentación Final
Cierre técnico y análisis.

- [ ] **Dashboard en Grafana:**
  - [ ] [cite_start]Conectar Grafana a InfluxDB[cite: 294].
  - [ ] [cite_start]Crear paneles para series de tiempo, predicciones (con superposición de valores) y un log tabular de las decisiones tomadas por el agente de n8n[cite: 295, 296, 297].
- [ ] **Informes Técnicos:**
  - [ ] [cite_start]Documentar análisis de seguridad y comparativa de rendimiento entre MQTT y CoAP[cite: 132, 134].
  - [ ] [cite_start]Desarrollar la arquitectura y el análisis de escalabilidad para un entorno industrial real (ej. sala de servidores o agricultura)[cite: 301, 307].