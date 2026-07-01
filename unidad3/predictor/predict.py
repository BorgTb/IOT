"""
Predictor de series de tiempo - Unidad 3
Lee el historial de sensores desde InfluxDB (measurement "sensor"),
proyecta a 30 min con regresion lineal (numpy.polyfit), publica la
prediccion por MQTT y la guarda en InfluxDB (measurement "prediccion")
para que Grafana superponga real vs. proyeccion.

Sensores reales del proyecto: CO2 (MQ7), sonido, distancia ultrasonica.
"""

import os
import json
import time
import numpy as np
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

# --- Config MQTT (1883, mismo que el resto del stack) ---
BROKER = os.getenv("MQTT_BROKER", "mosquitto")
PORT = int(os.getenv("MQTT_PORT", "1883"))
USER = os.getenv("MQTT_USER", "predictor")
PASS = os.getenv("MQTT_PASS", "predictor_iot")

# --- Config InfluxDB ---
INFLUX_HOST = os.getenv("INFLUXDB_HOST", "influxdb")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "smarthome_token_2024")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "smarthome")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "sensores")

TOPIC_PRED_CO2 = "smarthome/equipo2/prediccion/co2"
TOPIC_PRED_DIST = "smarthome/equipo2/prediccion/distancia"
TOPIC_ALERTA = "smarthome/equipo2/alerta"

UMBRAL_CO2 = float(os.getenv("UMBRAL_CO2", "400"))
HORIZON_MIN = int(os.getenv("HORIZON_MIN", "30"))
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "10"))


def query_serie(field):
    """Devuelve [(time, valor)] de las ultimas 6h para un campo del measurement 'sensor'."""
    try:
        from influxdb_client import InfluxDBClient
        client = InfluxDBClient(url=f"http://{INFLUX_HOST}:8086", token=INFLUX_TOKEN, org=INFLUX_ORG)
        q = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -6h)
          |> filter(fn: (r) => r._measurement == "sensor" and r._field == "{field}")
          |> sort(columns: ["_time"])
        '''
        datos = []
        for table in client.query_api().query(q):
            for row in table.records:
                datos.append((row.get_time(), float(row.get_value())))
        client.close()
        return datos
    except Exception as e:
        print(f"InfluxDB no disponible ({field}): {e}", flush=True)
        return []


def sintetico(base, amp, slope, n=20):
    """Datos de demostracion si aun no hay historial real."""
    now = datetime.now()
    return [(now - timedelta(minutes=(n - i) * 3), base + np.sin(i * 0.4) * amp + i * slope) for i in range(n)]


def predecir(datos, horizon_min=30):
    """Regresion lineal sobre los ultimos 20 valores. Devuelve (prediccion, pendiente, valor_actual)."""
    if len(datos) < 3:
        return None, None, None
    valores = np.array([v for _, v in datos[-20:]])
    x = np.arange(len(valores))
    coef = np.polyfit(x, valores, 1)
    tendencia = np.poly1d(coef)
    # cada muestra ~ 3 min -> avanzar horizon_min/3 pasos desde el ultimo punto
    x_pred = len(valores) - 1 + horizon_min / 3.0
    return float(tendencia(x_pred)), float(coef[0]), float(valores[-1])


def write_pred_influx(field, valor):
    """Guarda la prediccion en InfluxDB (measurement 'prediccion') para Grafana."""
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS
        client = InfluxDBClient(url=f"http://{INFLUX_HOST}:8086", token=INFLUX_TOKEN, org=INFLUX_ORG)
        w = client.write_api(write_options=SYNCHRONOUS)
        w.write(bucket=INFLUX_BUCKET, record=f"prediccion,horizon={HORIZON_MIN} {field}={valor}")
        client.close()
    except Exception as e:
        print(f"No se pudo escribir prediccion en Influx: {e}", flush=True)


def ciclo(client):
    # --- CO2 (MQ7) ---
    co2 = query_serie("co2")
    if len(co2) < 3:
        print("Pocos datos reales de CO2, usando datos sinteticos", flush=True)
        co2 = sintetico(350, 50, 2)

    pred_co2, pend_co2, actual_co2 = predecir(co2, HORIZON_MIN)
    now = datetime.now().isoformat()

    if pred_co2 is not None:
        msg = {"valor": round(pred_co2, 1), "horizon_min": HORIZON_MIN,
               "pendiente": round(pend_co2, 3), "timestamp": now}
        client.publish(TOPIC_PRED_CO2, json.dumps(msg))
        write_pred_influx("co2", round(pred_co2, 1))
        print(f"Prediccion CO2 {HORIZON_MIN}min: {pred_co2:.1f} ppm "
              f"(actual {actual_co2:.0f}, pendiente {pend_co2:.2f})", flush=True)

        # Alerta preventiva: superara el umbral aunque ahora este por debajo
        if pred_co2 > UMBRAL_CO2 and actual_co2 <= UMBRAL_CO2:
            alerta = {
                "tipo": "preventiva",
                "sensor": "co2",
                "valor_actual": round(actual_co2, 1),
                "prediccion": round(pred_co2, 1),
                "horizonte_min": HORIZON_MIN,
                "mensaje": f"CO2 podria alcanzar {pred_co2:.0f} ppm en {HORIZON_MIN} min"
            }
            client.publish(TOPIC_ALERTA, json.dumps(alerta))
            print(f"ALERTA preventiva: {alerta['mensaje']}", flush=True)

    # --- DISTANCIA (opcional, si hay datos reales) ---
    dist = query_serie("distancia")
    if len(dist) >= 3:
        pred_d, _, _ = predecir(dist, HORIZON_MIN)
        if pred_d is not None:
            client.publish(TOPIC_PRED_DIST, json.dumps({"valor": round(pred_d, 1), "horizon_min": HORIZON_MIN}))
            write_pred_influx("distancia", round(pred_d, 1))


def on_message(client, userdata, msg):
    """Actualiza el umbral de CO2 cuando el chat lo cambia (topico retenido)."""
    global UMBRAL_CO2
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        if "limite" in data:
            UMBRAL_CO2 = float(data["limite"])
            print(f"Umbral CO2 actualizado a {UMBRAL_CO2} ppm (configurado desde el chat)", flush=True)
    except Exception as e:
        print(f"Error procesando umbral: {e}", flush=True)


def on_connect(client, userdata, flags, rc, props=None):
    print(f"MQTT conectado rc={rc}", flush=True)
    client.subscribe("smarthome/equipo2/umbrales/co2")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USER, PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except Exception as e:
            print(f"Esperando broker MQTT: {e}", flush=True)
            time.sleep(5)

    client.loop_start()
    print(f"Predictor iniciado. Intervalo {INTERVAL_MIN} min, horizonte {HORIZON_MIN} min", flush=True)

    while True:
        try:
            ciclo(client)
        except Exception as e:
            print(f"Error en ciclo de prediccion: {e}", flush=True)
        print(f"Esperando {INTERVAL_MIN} minutos...", flush=True)
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
