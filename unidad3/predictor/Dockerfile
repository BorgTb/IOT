FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt numpy influxdb-client

COPY predict.py .
COPY ../../mosquitto/certs/ca.crt ca.crt

CMD ["python", "predict.py"]
