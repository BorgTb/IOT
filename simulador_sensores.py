"""
Simulador de sensores del nodo MKR1000 (distancia, gas/CO2, sonido).

Publica por MQTT exactamente lo mismo que el firmware ProyectoIOT.ino:
  - JSON combinado en  smarthome/equipo2/alerta   (lo que consume Node-RED)
  - Valores sueltos en smarthome/equipo2/co2, /sonido, /distancia

NO simula deteccion de personas: eso lo hace la ESP32-CAM fisica + api-ia.

Uso:
    python simulador_sensores.py                # TLS al broker local (8883)
    python simulador_sensores.py --plain        # sin TLS (1883)
    python simulador_sensores.py --interval 5   # publicar cada 5 segundos
    python simulador_sensores.py --broker 192.168.1.10

Requiere: pip install paho-mqtt
"""

import argparse
import json
import os
import random
import ssl
import sys
import time

import paho.mqtt.client as mqtt

# Credenciales del nodo de sensores (ver mosquitto/config/passwd y acl.acl)
USER = "mkr1000"
PASS = "mkr1000_iot"

TOPIC_ALERTA    = "smarthome/equipo2/alerta"
TOPIC_CO2       = "smarthome/equipo2/co2"
TOPIC_SONIDO    = "smarthome/equipo2/sonido"
TOPIC_DISTANCIA = "smarthome/equipo2/distancia"

CA_CERT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "mosquitto", "certs", "ca.crt")


class Sensor:
    """Camina aleatoriamente dentro de un rango, con picos ocasionales."""

    def __init__(self, nombre, minimo, maximo, paso, pico_max, prob_pico):
        self.nombre = nombre
        self.min = minimo
        self.max = maximo
        self.paso = paso
        self.pico_max = pico_max
        self.prob_pico = prob_pico
        self.valor = random.uniform(minimo, maximo)
        self.pico_restante = 0

    def leer(self):
        if self.pico_restante > 0:
            self.pico_restante -= 1
        elif random.random() < self.prob_pico:
            # Inicia un pico anomalo que dura algunas lecturas
            self.pico_restante = random.randint(3, 6)
            print(f"  >> pico anomalo en {self.nombre}!")

        if self.pico_restante > 0:
            objetivo = self.pico_max
            self.valor += (objetivo - self.valor) * 0.5
        else:
            self.valor += random.uniform(-self.paso, self.paso)
            self.valor = max(self.min, min(self.max, self.valor))
        return self.valor


def conectar(broker, port, use_tls):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USER, PASS)
    if use_tls:
        client.tls_set(CA_CERT, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        # El certificado esta emitido para el hostname del broker en Docker,
        # no para localhost: deshabilitamos la verificacion de hostname.
        client.tls_insecure_set(True)

    conectado = {"ok": False, "rc": None}

    def on_connect(cli, userdata, flags, rc, properties=None):
        conectado["ok"] = (rc == 0)
        conectado["rc"] = rc

    client.on_connect = on_connect
    client.connect(broker, port, keepalive=30)
    client.loop_start()

    for _ in range(50):  # esperar hasta 5 s la confirmacion CONNACK
        if conectado["rc"] is not None:
            break
        time.sleep(0.1)

    if not conectado["ok"]:
        raise ConnectionError(f"CONNACK rc={conectado['rc']}")
    return client


def main():
    parser = argparse.ArgumentParser(description="Simulador de sensores MKR1000")
    parser.add_argument("--broker", default="localhost", help="Host del broker MQTT")
    parser.add_argument("--port", type=int, default=None, help="Puerto (default 8883 TLS / 1883 plano)")
    parser.add_argument("--plain", action="store_true", help="Conectar sin TLS (puerto 1883)")
    parser.add_argument("--interval", type=float, default=3.0, help="Segundos entre publicaciones")
    args = parser.parse_args()

    use_tls = not args.plain
    port = args.port or (8883 if use_tls else 1883)

    print(f"Conectando a {args.broker}:{port} ({'TLS' if use_tls else 'sin TLS'}) como '{USER}'...")
    try:
        client = conectar(args.broker, port, use_tls)
    except Exception as e:
        print(f"Error al conectar: {e}")
        if use_tls:
            print("Reintentando sin TLS en el puerto 1883...")
            try:
                client = conectar(args.broker, 1883, False)
            except Exception as e2:
                print(f"Tampoco funciono sin TLS: {e2}")
                sys.exit(1)
        else:
            sys.exit(1)

    print("Conectado. Publicando sensores simulados (Ctrl+C para detener).\n")

    # Rangos normales calibrados con los umbrales del sistema:
    # los picos superan el umbral para poder probar las alertas.
    gas       = Sensor("gas/CO2",  40,  120, paso=8,  pico_max=400, prob_pico=0.02)
    sonido    = Sensor("sonido",   30,   70, paso=6,  pico_max=98,  prob_pico=0.02)
    distancia = Sensor("distancia", 60, 150, paso=10, pico_max=18,  prob_pico=0.02)

    try:
        while True:
            valor_gas = round(gas.leer())
            valor_sonido = round(sonido.leer())
            valor_distancia = round(distancia.leer(), 1)

            payload = {
                "equipo": "equipo2",
                "co2": valor_gas,
                "gas": valor_gas,
                "sonido": valor_sonido,
                "distancia": valor_distancia,
            }

            client.publish(TOPIC_ALERTA, json.dumps(payload))
            client.publish(TOPIC_CO2, str(valor_gas))
            client.publish(TOPIC_SONIDO, str(valor_sonido))
            client.publish(TOPIC_DISTANCIA, str(valor_distancia))

            print(f"[{time.strftime('%H:%M:%S')}] gas={valor_gas} ppm | "
                  f"sonido={valor_sonido} % | distancia={valor_distancia} cm")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nSimulacion detenida.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
