import os
import sys
import json
import time
import numpy as np
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

BROKER = os.getenv("MQTT_BROKER", "mosquitto")
PORT = int(os.getenv("MQTT_PORT", "8883"))
TOPIC_PRED_TEMP = "smarthome/equipo2/prediccion/temperatura"
TOPIC_PRED_GAS = "smarthome/equipo2/prediccion/gas"
TOPIC_ALERTA = "smarthome/equipo2/alerta"
USER = "predictor"
PASS = "predictor_iot"
CA_CERT = "/app/ca.crt"

UMBRAL_TEMP = 35
UMBRAL_GAS = 400
HORIZON_MIN = 30
INTERVAL_MIN = 10

datos_temperatura = []
datos_gas = []

def on_connect(client, userdata, flags, rc):
    print(f"Conectado a MQTT con código {rc}")

def cargar_datos_desde_influx():
    try:
        from influxdb_client import InfluxDBClient
        client = InfluxDBClient(
            url=f"http://{os.getenv('INFLUXDB_HOST', 'influxdb')}:8086",
            token=os.getenv("INFLUXDB_TOKEN", "smarthome_token_2024"),
            org="smarthome"
        )
        query = f'''
        from(bucket: "sensores")
            |> range(start: -6h)
            |> filter(fn: (r) => r["_measurement"] == "sensor")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        tables = client.query_api().query(query)
        for table in tables:
            for row in table.records:
                ts = row.values["_time"]
                temp = row.values.get("temperatura")
                gas = row.values.get("gas")
                if temp is not None:
                    datos_temperatura.append((ts, float(temp)))
                if gas is not None:
                    datos_gas.append((ts, float(gas)))
        print(f"Cargados {len(datos_temperatura)} temp, {len(datos_gas)} gas desde InfluxDB")
        client.close()
    except Exception as e:
        print(f"InfluxDB no disponible: {e}, usando datos sintéticos")

    if not datos_temperatura:
        print("Generando datos sintéticos para demostración")
        now = datetime.now()
        for i in range(20):
            ts = now - timedelta(minutes=i*3)
            datos_temperatura.append((ts, 28 + np.sin(i*0.5)*3 + i*0.1))
            datos_gas.append((ts, 350 + np.sin(i*0.3)*50 + i*2))

def predecir(datos, horizon_min=30):
    if len(datos) < 3:
        return None, None
    valores = np.array([v for _, v in datos[-20:]])
    x = np.arange(len(valores))
    coef = np.polyfit(x, valores, 1)
    tendencia = np.poly1d(coef)
    x_pred = len(valores) + horizon_min / 3
    prediccion = float(tendencia(x_pred))
    return prediccion, float(coef[0])

def publicar_prediccion(client):
    pred_temp, pend_temp = predecir(datos_temperatura, HORIZON_MIN)
    pred_gas, pend_gas = predecir(datos_gas, HORIZON_MIN)

    now = datetime.now().isoformat()

    if pred_temp is not None:
        msg = {"valor": round(pred_temp, 1), "horizon_min": HORIZON_MIN, "timestamp": now}
        client.publish(TOPIC_PRED_TEMP, json.dumps(msg))
        print(f"Predicción temperatura: {pred_temp:.1f}°C")

    if pred_gas is not None:
        msg = {"valor": round(pred_gas, 1), "horizon_min": HORIZON_MIN, "timestamp": now}
        client.publish(TOPIC_PRED_GAS, json.dumps(msg))
        print(f"Predicción gas: {pred_gas:.1f} ppm")

    if pred_temp and pred_temp > UMBRAL_TEMP:
        alerta = {
            "tipo": "preventiva",
            "sensor": "temperatura",
            "valor_actual": round(datos_temperatura[-1][1], 1) if datos_temperatura else 0,
            "prediccion": round(pred_temp, 1),
            "horizonte_min": HORIZON_MIN,
            "mensaje": f"Temperatura podría alcanzar {pred_temp:.0f}°C en {HORIZON_MIN} min"
        }
        client.publish(TOPIC_ALERTA, json.dumps(alerta))
        print(f"⚠ Alerta preventiva: {alerta['mensaje']}")

    if pred_gas and pred_gas > UMBRAL_GAS:
        alerta = {
            "tipo": "preventiva",
            "sensor": "gas",
            "valor_actual": round(datos_gas[-1][1], 1) if datos_gas else 0,
            "prediccion": round(pred_gas, 1),
            "horizonte_min": HORIZON_MIN,
            "mensaje": f"Gas podría alcanzar {pred_gas:.0f} ppm en {HORIZON_MIN} min"
        }
        client.publish(TOPIC_ALERTA, json.dumps(alerta))
        print(f"⚠ Alerta preventiva: {alerta['mensaje']}")

def main():
    cargar_datos_desde_influx()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USER, PASS)
    client.tls_set(CA_CERT)
    client.on_connect = on_connect

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"Error conectando a MQTT: {e}")
        sys.exit(1)

    print(f"Predictor iniciado. Publicando cada {INTERVAL_MIN} minutos...")
    try:
        while True:
            publicar_prediccion(client)
            print(f"Esperando {INTERVAL_MIN} minutos...")
            time.sleep(INTERVAL_MIN * 60)
    except KeyboardInterrupt:
        print("Deteniendo predictor...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
