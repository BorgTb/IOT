FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiocoap paho-mqtt

COPY coap_server.py .

CMD ["python", "coap_server.py"]
