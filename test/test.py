# -*- coding: utf-8 -*-
"""Simulador interactivo de la estacion IoT.

Permite simular lecturas de sensores (via MQTT, igual que el MKR1000) y
detecciones de personas con rostro (via el endpoint /simular/camara de
Node-RED, que pasa por el reconocimiento facial real de api-ia).
"""
import base64
import json
import os
import random
import ssl
import sys
import time
import urllib.request
import urllib.error

import paho.mqtt.client as mqtt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BROKER = "localhost"
PORT_TLS = 8883
PORT_PLAIN = 1883
TOPIC = "smarthome/equipo2/alerta"
USER = "mkr1000"
PASS = "mkr1000_iot"
CA_CERT = os.path.join(BASE_DIR, "mosquitto", "certs", "ca.crt")

NODERED = "http://localhost:1880"
IMAGENES_DB = os.path.join(BASE_DIR, "api-ia", "imagenes_db")

_client = None


# ─── MQTT ────────────────────────────────────────────────────────────────

def conectar_mqtt():
    """Conecta una sola vez; TLS primero y sin TLS como respaldo."""
    global _client
    if _client is not None:
        return _client

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"  Conectado al broker MQTT ({BROKER})")
        else:
            print(f"  Error al conectar, codigo: {rc}")

    try:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        c.username_pw_set(USER, PASS)
        c.tls_set(CA_CERT, tls_version=ssl.PROTOCOL_TLS)
        c.on_connect = on_connect
        c.connect(BROKER, PORT_TLS, 60)
        c.loop_start()
        _client = c
    except Exception as e:
        print(f"  TLS fallo ({e}); intentando sin TLS en {PORT_PLAIN}...")
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        c.username_pw_set(USER, PASS)
        c.on_connect = on_connect
        c.connect(BROKER, PORT_PLAIN, 60)
        c.loop_start()
        _client = c
    time.sleep(1)
    return _client


def publicar(payload):
    client = conectar_mqtt()
    mensaje = json.dumps(payload)
    client.publish(TOPIC, mensaje)
    print(f"  Publicado en {TOPIC} -> {mensaje}")


def lectura_normal():
    return {
        "distancia": round(random.uniform(40.0, 150.0), 1),
        "gas": random.randint(50, 120),
        "sonido": random.randint(30, 60),
    }


def sim_sensores_normales():
    publicar(lectura_normal())
    print("  Valores dentro de rango: la IA no deberia alertar.")


def sim_sensores_continuo():
    print("  Publicando cada 3 s. Ctrl+C para volver al menu.")
    try:
        while True:
            publicar(lectura_normal())
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n  Simulacion continua detenida.")


def sim_co2_alto():
    p = lectura_normal()
    p["gas"] = random.randint(450, 600)
    publicar(p)
    print("  CO2 sobre el umbral de referencia (400 ppm).")
    print("  La IA evalua como maximo 1 vez por minuto: revisa el LED y Telegram.")


def sim_sonido_alto():
    p = lectura_normal()
    p["sonido"] = random.randint(90, 110)
    publicar(p)
    print("  Sonido sobre el umbral de referencia (80 dB).")
    print("  La IA evalua como maximo 1 vez por minuto: revisa el LED y Telegram.")


def sim_distancia_baja():
    p = lectura_normal()
    p["distancia"] = round(random.uniform(3.0, 15.0), 1)
    publicar(p)
    print("  Distancia bajo el umbral de referencia (20 cm).")
    print("  La IA evalua como maximo 1 vez por minuto: revisa el LED y Telegram.")


# ─── Deteccion de personas ───────────────────────────────────────────────

def enviar_imagen(ruta):
    """Envia una imagen a Node-RED, que la pasa por el reconocimiento facial real."""
    with open(ruta, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    datos = json.dumps({"image": b64}).encode("utf-8")
    req = urllib.request.Request(
        NODERED + "/simular/camara",
        data=datos,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"  Enviando {os.path.basename(ruta)} al reconocimiento facial...")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            r = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"  Error llamando a Node-RED: {e}")
        print("  ¿Esta corriendo el contenedor nodered (puerto 1880)?")
        return

    resultado = r.get("resultado", {})
    if not resultado.get("persona"):
        print("  Resultado: NO se detecto ningun rostro en la imagen.")
        return

    if resultado.get("reconocida"):
        print(f"  Resultado: persona CONOCIDA -> {resultado.get('nombre')}")
    else:
        print("  Resultado: persona DESCONOCIDA (posible INTRUSO)")
    print("  Se actualizo el dashboard (pestana Seguridad) y, si es una visita")
    print("  nueva (ventana de 5 min), llega la alerta con foto por Telegram.")


def listar_registradas():
    if not os.path.isdir(IMAGENES_DB):
        return []
    personas = []
    for d in sorted(os.listdir(IMAGENES_DB)):
        carpeta = os.path.join(IMAGENES_DB, d)
        if os.path.isdir(carpeta):
            fotos = [f for f in os.listdir(carpeta)
                     if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
            if fotos:
                personas.append((d, os.path.join(carpeta, fotos[0])))
    return personas


def sim_persona_conocida():
    personas = listar_registradas()
    if not personas:
        print("  No hay personas registradas con fotos en api-ia/imagenes_db.")
        print("  Registra a alguien desde el dashboard primero.")
        return
    print("  Personas registradas:")
    for i, (nombre, _) in enumerate(personas, 1):
        print(f"    {i}) {nombre}")
    eleccion = input("  Elige numero (Enter = 1): ").strip() or "1"
    try:
        nombre, ruta = personas[int(eleccion) - 1]
    except (ValueError, IndexError):
        print("  Opcion invalida.")
        return
    print(f"  Simulando que la camara ve a '{nombre}'...")
    enviar_imagen(ruta)


def sim_intruso():
    print("  Para simular un intruso se necesita la foto de un rostro que NO")
    print("  este registrado (una foto tuya de otra persona, bajada de internet, etc.)")
    ruta = input("  Ruta de la imagen (jpg/png): ").strip().strip('"')
    if not ruta or not os.path.isfile(ruta):
        print("  No se encontro el archivo.")
        return
    enviar_imagen(ruta)


# ─── Estado ──────────────────────────────────────────────────────────────

def ver_gemelo():
    try:
        with urllib.request.urlopen(NODERED + "/gemelo/estado", timeout=10) as resp:
            g = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"  Error consultando el gemelo: {e}")
        return
    e = g.get("estado_actual", {})
    print("  Estado actual del gemelo digital:")
    print(f"    CO2:       {e.get('co2')} ppm")
    print(f"    Distancia: {e.get('distancia')} cm")
    print(f"    Sonido:    {e.get('sonido')} dB")
    print(f"    Persona:   {'si' if e.get('persona') else 'no'}"
          + (f" ({e.get('persona_nombre')})" if e.get('persona_nombre') else ""))
    print(f"    LED:       {'encendido' if e.get('led') else 'apagado'}")
    up = g.get("ultima_persona")
    if up:
        print(f"    Ultima persona: {up.get('nombre')} ({up.get('estado')}) a las {up.get('hora')}")
    if g.get("resumen_llm"):
        print(f"    Ultimo razonamiento IA: {g.get('resumen_llm')}")


# ─── Menu ────────────────────────────────────────────────────────────────

MENU = """
========= SIMULADOR ESTACION IOT =========
  Sensores (MQTT, como el MKR1000)
    1) Lectura normal (una vez)
    2) Lecturas normales continuas
    3) Alerta: CO2 alto
    4) Alerta: sonido alto
    5) Alerta: distancia baja
  Camara (reconocimiento facial real)
    6) Detectar persona CONOCIDA
    7) Detectar INTRUSO (foto no registrada)
  Otros
    8) Ver estado del gemelo digital
    0) Salir
==========================================="""

ACCIONES = {
    "1": sim_sensores_normales,
    "2": sim_sensores_continuo,
    "3": sim_co2_alto,
    "4": sim_sonido_alto,
    "5": sim_distancia_baja,
    "6": sim_persona_conocida,
    "7": sim_intruso,
    "8": ver_gemelo,
}


def main():
    print("Simulador de la estacion IoT — las decisiones las toma la IA;")
    print("aqui solo se generan los estimulos (sensores y camara).")
    while True:
        print(MENU)
        opcion = input("Opcion: ").strip()
        if opcion == "0":
            break
        accion = ACCIONES.get(opcion)
        if accion is None:
            print("  Opcion invalida.")
            continue
        try:
            accion()
        except KeyboardInterrupt:
            print("\n  Interrumpido.")
        except Exception as e:
            print(f"  Error: {e}")

    if _client is not None:
        _client.loop_stop()
        _client.disconnect()
    print("Hasta luego.")


if __name__ == "__main__":
    main()
