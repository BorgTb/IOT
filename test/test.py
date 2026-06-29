import time
import random
import json
import ssl
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 8883
TOPIC = "smarthome/equipo2/alerta"
USER = "mkr1000"
PASS = "mkr1000_iot"
CA_CERT = "mosquitto/certs/ca.crt"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Conectado al broker MQTT TLS en {BROKER}:{PORT}")
    else:
        print(f"Error al conectar, código: {rc}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USER, PASS)
client.tls_set(CA_CERT, tls_version=ssl.PROTOCOL_TLS)
client.on_connect = on_connect

print("Conectando al broker MQTT con TLS...")
try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()
except Exception as e:
    print(f"Error al conectar: {e}")
    print("Intentando sin TLS (puerto 1883)...")
    try:
        client2 = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client2.username_pw_set(USER, PASS)
        client2.connect("localhost", 1883, 60)
        client2.loop_start()
        client = client2
    except Exception as e2:
        print(f"Error sin TLS: {e2}")
        exit(1)

print("Iniciando simulacion de sensores. Ctrl+C para detener.\n")

try:
    while True:
        distancia = round(random.uniform(15.0, 150.0), 1)
        gas = random.randint(50, 120)
        sonido = random.randint(40, 95)

        payload = {
            "distancia": distancia,
            "gas": gas,
            "sonido": sonido
        }

        mensaje_json = json.dumps(payload)
        client.publish(TOPIC, mensaje_json)
        print(f"Publicado en {TOPIC} -> {mensaje_json}")
        time.sleep(3)

except KeyboardInterrupt:
    print("\nSimulacion detenida.")
    client.loop_stop()
    client.disconnect()
