import time
import random
import json
import paho.mqtt.client as mqtt

# Configuraciones basadas en tu flujo de Node-RED
BROKER = "192.168.1.7"
PORT = 1883
TOPIC = "smarthome/equipo2/alerta"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Conectado al broker MQTT en {BROKER}:{PORT}")
    else:
        print(f"❌ Error al conectar, código: {rc}")

# Configurar el cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect

print("Intentando conectar al broker MQTT...")
try:
    client.connect(BROKER, PORT, 60)
    client.loop_start() # Iniciar el loop de MQTT en segundo plano
except Exception as e:
    print(f"Error crítico al conectar: {e}")
    exit(1)

print("Iniciando simulación de sensores. Presiona Ctrl+C para detener.\n")

try:
    while True:
        # Generar valores aleatorios
        # Distancia: 15 a 150 cm (caerá por debajo de 20 a veces para probar la alerta)
        distancia = round(random.uniform(15.0, 150.0), 1)
        
        # Gas: 50 a 120 (superará el 100 a veces)
        gas = random.randint(50, 120)
        
        # Sonido: 40 a 95% (superará el 80 a veces)
        sonido = random.randint(40, 95)

        # Armar el JSON exactamente como lo espera el nodo "Parsear JSON" de Node-RED
        payload = {
            "distancia": distancia,
            "gas": gas,
            "sonido": sonido
        }

        # Convertir a string JSON y publicar
        mensaje_json = json.dumps(payload)
        client.publish(TOPIC, mensaje_json)
        
        print(f"📡 Publicado en {TOPIC} -> {mensaje_json}")

        # Esperar 3 segundos antes del siguiente envío (puedes ajustar este tiempo)
        time.sleep(3)

except KeyboardInterrupt:
    print("\n🛑 Simulación detenida por el usuario.")
    client.loop_stop()
    client.disconnect()