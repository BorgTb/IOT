"""
Puente CoAP -> MQTT (Unidad 2, funcionalidad 5.2)
Servidor CoAP (UDP 5683) que recibe los recursos publicados por el nodo sensor
ESP32 de bajo consumo (temperatura / humedad vía CoAP-simple-library) y los
redirige al broker MQTT.

Se implementa con aiocoap (en vez de node-red-contrib-coap, que no es compatible
con Node.js 20). Cumple el requisito: "recibir los recursos CoAP y redirigir los
datos al broker MQTT".
"""

import asyncio
import json
import os

import aiocoap
import aiocoap.resource as resource
import paho.mqtt.client as mqtt

BROKER = os.getenv("MQTT_BROKER", "mosquitto")
PORT = int(os.getenv("MQTT_PORT", "1883"))
USER = os.getenv("MQTT_USER", "coap")
PASS = os.getenv("MQTT_PASS", "coap_iot")
COAP_PORT = int(os.getenv("COAP_PORT", "5683"))

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.username_pw_set(USER, PASS)


class SensorResource(resource.Resource):
    """Recurso CoAP que acepta PUT y reenvía el dato a MQTT."""

    def __init__(self, tipo):
        super().__init__()
        self.tipo = tipo

    async def render_put(self, request):
        texto = request.payload.decode("utf-8", errors="ignore")
        tipo = self.tipo
        valor = texto
        try:
            data = json.loads(texto)
            valor = data.get("valor", texto)
            tipo = data.get("tipo", self.tipo)
        except (ValueError, AttributeError):
            try:
                valor = float(texto)
            except ValueError:
                pass

        topic = f"smarthome/equipo2/{tipo}"
        msg = json.dumps({"valor": valor, "fuente": "coap"})
        mqttc.publish(topic, msg, qos=1)
        print(f"CoAP PUT /{tipo} -> MQTT {topic} = {msg}", flush=True)
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"OK")


async def main():
    while True:
        try:
            mqttc.connect(BROKER, PORT, 60)
            break
        except Exception as e:
            print(f"Esperando broker MQTT: {e}", flush=True)
            await asyncio.sleep(5)
    mqttc.loop_start()

    root = resource.Site()
    root.add_resource(["temperatura"], SensorResource("temperatura"))
    root.add_resource(["humedad"], SensorResource("humedad"))
    root.add_resource(["distancia"], SensorResource("distancia"))
    root.add_resource(["co2"], SensorResource("co2"))
    root.add_resource(["sonido"], SensorResource("sonido"))

    await aiocoap.Context.create_server_context(root, bind=("0.0.0.0", COAP_PORT))
    print(f"Servidor CoAP escuchando en UDP {COAP_PORT}", flush=True)

    # correr indefinidamente
    await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
