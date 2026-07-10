FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libcoap3-bin && rm -rf /var/lib/apt/lists/* && ln -s /usr/bin/coap-client-gnutls /usr/bin/coap-client
RUN pip install --no-cache-dir aiocoap paho-mqtt

COPY coap_server.py .

CMD ["python", "coap_server.py"]
