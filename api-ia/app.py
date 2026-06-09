"""
API de Reconocimiento Facial - Sistema de Asistencia
Servicio Flask que procesa imagenes, reconoce rostros y se comunica con el backend
Usa una base de datos interna de imagenes organizadas por nombre en imagenes_db/
"""

import os
import pickle
import base64
import cv2
import numpy as np
import face_recognition
from flask import Flask, request, jsonify
from flask_cors import CORS

# ==========================================
# CONFIGURACION
# ==========================================

app = Flask(__name__)
CORS(app)

# Base de datos interna de imagenes
IMAGENES_DB = "imagenes_db"

# Archivo cache de encodings (mantenido para velocidad)
DATOS_ROSTROS = "rostros_conocidos.dat"

# Cargar rostros conocidos al iniciar
nombres_conocidos = []
encodings_conocidos = []

def cargar_imagenes_locales():
    """
    Escanea la carpeta imagenes_db/ y carga todas las imagenes.
    Estructura esperada:
        imagenes_db/
            Nombre Persona/
                foto1.jpg
                foto2.png
            Otra Persona/
                foto1.jpg
    Retorna (nombres, encodings).
    """
    nombres = []
    encodings = []

    if not os.path.exists(IMAGENES_DB):
        print(f"Creando directorio {IMAGENES_DB}/...")
        os.makedirs(IMAGENES_DB, exist_ok=True)
        return nombres, encodings

    personas = [d for d in os.listdir(IMAGENES_DB)
                if os.path.isdir(os.path.join(IMAGENES_DB, d))]

    print(f"Escaneando {len(personas)} personas en {IMAGENES_DB}/...")

    for persona in personas:
        dir_persona = os.path.join(IMAGENES_DB, persona)
        imagenes = [f for f in os.listdir(dir_persona)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]

        if not imagenes:
            print(f"  {persona}: sin imagenes validas, omitiendo")
            continue

        encodings_persona = []
        for img_name in imagenes:
            ruta = os.path.join(dir_persona, img_name)
            try:
                frame = cv2.imread(ruta)
                if frame is None:
                    print(f"  {persona}/{img_name}: no se pudo leer")
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb, model="hog")
                face_encodings_list = face_recognition.face_encodings(rgb, face_locations)

                if face_encodings_list:
                    encodings_persona.append(face_encodings_list[0])
                    print(f"  {persona}/{img_name}: rostro detectado OK")
                else:
                    print(f"  {persona}/{img_name}: sin rostro detectable")

            except Exception as e:
                print(f"  {persona}/{img_name}: error - {e}")

        if encodings_persona:
            # Promediar todos los encodings de la persona para tener uno solo
            encoding_promedio = np.mean(encodings_persona, axis=0)
            nombres.append(persona)
            encodings.append(encoding_promedio)
            print(f"  {persona}: {len(encodings_persona)} rostro(s) cargado(s) -> encoding promedio")
        else:
            print(f"  {persona}: no se pudo generar ningun encoding")

    return nombres, encodings


print("Cargando rostros desde imagenes_db/...")
try:
    nombres_conocidos, encodings_conocidos = cargar_imagenes_locales()
    print(f"Se cargaron {len(nombres_conocidos)} personas desde imagenes_db/")

    # Intentar guardar cache para arranques futuros mas rapidos
    if nombres_conocidos:
        guardar_rostros()
except Exception as e:
    print(f"Error cargando imagenes locales: {e}")
    print("Intentando cargar desde archivo cache...")
    try:
        with open(DATOS_ROSTROS, "rb") as f:
            datos_guardados = pickle.load(f)
            nombres_conocidos = datos_guardados['nombres']
            encodings_conocidos = datos_guardados['encodings']
        print(f"Se cargaron {len(nombres_conocidos)} rostros desde cache.")
    except (FileNotFoundError, EOFError):
        print("No se encontro archivo de datos. Empezando desde cero.")


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def guardar_rostros():
    """Guarda la lista de nombres y encodings en un archivo cache."""
    if not nombres_conocidos:
        print("No hay datos que guardar.")
        return

    print(f"Guardando {len(nombres_conocidos)} rostros en cache...")
    try:
        with open(DATOS_ROSTROS, "wb") as f:
            pickle.dump({
                'nombres': nombres_conocidos,
                'encodings': encodings_conocidos
            }, f)
        print("Datos guardados exitosamente!")
    except Exception as e:
        print(f"Error al guardar los datos: {e}")


def sincronizar_encodings():
    """Recarga los encodings desde la DB local de imagenes."""
    global nombres_conocidos, encodings_conocidos
    print("Recargando encodings desde DB local...", flush=True)
    nombres_conocidos, encodings_conocidos = cargar_imagenes_locales()
    guardar_rostros()
    print(f"Recargados {len(nombres_conocidos)} encodings", flush=True)



def imagen_base64_a_array(imagen_base64):
    """Convierte una imagen base64 a array numpy para OpenCV."""
    try:
        if ',' in imagen_base64:
            imagen_base64 = imagen_base64.split(',')[1]

        img_bytes = base64.b64decode(imagen_base64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)

        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("No se pudo decodificar la imagen")

        return frame
    except Exception as e:
        raise ValueError(f"Error decodificando imagen: {e}")


def procesar_frame_reconocimiento(frame):
    """
    Procesa un frame y reconoce rostros.
    Retorna lista de rostros detectados con sus datos.
    """
    rgb_small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(rgb_small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame, model="cnn")
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    rostros_detectados = []

    for i, face_encoding in enumerate(face_encodings):
        top, right, bottom, left = face_locations[i]
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        usuario_id = None
        confianza = 0.0
        nombre = "Desconocido"

        if len(encodings_conocidos) > 0:
            distancias = face_recognition.face_distance(encodings_conocidos, face_encoding)
            mejor_indice = np.argmin(distancias)
            mejor_distancia = distancias[mejor_indice]

            if mejor_distancia < 0.6:
                usuario_id = nombres_conocidos[mejor_indice]
                confianza = 1.0 - mejor_distancia
                nombre = nombres_conocidos[mejor_indice]

        rostros_detectados.append({
            'usuario_id': usuario_id,
            'nombre': nombre,
            'confianza': round(confianza, 3),
            'reconocido': usuario_id is not None,
            'bbox': {
                'left': int(left),
                'top': int(top),
                'width': int(right - left),
                'height': int(bottom - top)
            }
        })

    return rostros_detectados


def recargar_db():
    """Recarga todos los encodings desde imagenes_db/."""
    global nombres_conocidos, encodings_conocidos
    print("Recargando base de datos de imagenes locales...")
    nombres_conocidos, encodings_conocidos = cargar_imagenes_locales()
    guardar_rostros()
    print(f"DB recargada: {len(nombres_conocidos)} personas en memoria")


# ==========================================
# RUTAS DE LA API
# ==========================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'api-ia-reconocimiento',
        'rostros_cargados': len(nombres_conocidos),
        'db_local': IMAGENES_DB
    }), 200


@app.route('/recognize', methods=['POST'])
def recognize():
    """
    Procesa una imagen y reconoce rostros.

    Body (JSON):
    {
        "image": "data:image/jpeg;base64,..." o base64 directo
    }

    Respuesta:
    {
        "success": true,
        "rostros": [
            {
                "nombre": "Juan Perez",
                "confianza": 0.952,
                "reconocido": true,
                "bbox": { "left": 100, "top": 50, "width": 200, "height": 250 }
            }
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'message': 'No se proporciono imagen'
            }), 400

        frame = imagen_base64_a_array(data['image'])
        rostros = procesar_frame_reconocimiento(frame)

        return jsonify({
            'success': True,
            'rostros': rostros,
            'total_detectados': len(rostros)
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"Error en /recognize: {e}")
        return jsonify({
            'success': False,
            'message': 'Error procesando imagen'
        }), 500



@app.route('/train', methods=['POST'])
def train():
    """
    Registra uno o multiples rostros de una persona en la DB interna.

    Body (JSON):
    {
        "nombre": "Juan Perez",
        "imagenes": ["data:image/jpeg;base64,...", ...]
    }

    O formato simple:
    {
        "nombre": "Juan Perez",
        "image": "data:image/jpeg;base64,..."
    }
    """
    try:
        data = request.get_json()
        print(f"=== TRAIN REQUEST ===")
        print(f"Data keys: {data.keys() if data else 'None'}")

        if not data or 'nombre' not in data:
            return jsonify({
                'success': False,
                'message': 'Se requiere nombre'
            }), 400

        nombre = data['nombre'].strip()
        if not nombre:
            return jsonify({
                'success': False,
                'message': 'El nombre no puede estar vacio'
            }), 400

        imagenes = []
        if 'imagenes' in data and isinstance(data['imagenes'], list):
            imagenes = data['imagenes']
        elif 'image' in data:
            imagenes = [data['image']]
        else:
            return jsonify({
                'success': False,
                'message': 'Se requiere al menos una imagen (image o imagenes[])'
            }), 400

        nuevos_encodings = []
        rostros_procesados = 0
        errores = []
        rutas_guardadas = []

        # Crear directorio para la persona
        dir_persona = os.path.join(IMAGENES_DB, nombre)
        os.makedirs(dir_persona, exist_ok=True)

        for idx, imagen_b64 in enumerate(imagenes):
            try:
                frame = imagen_base64_a_array(imagen_b64)

                # Guardar imagen en disco
                ext = ".jpg"
                ruta_img = os.path.join(dir_persona, f"rostro_{idx + 1}{ext}")
                cv2.imwrite(ruta_img, frame)
                rutas_guardadas.append(ruta_img)

                # Procesar para encoding
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb_frame.shape[:2]
                print(f"Imagen {idx + 1}: {w}x{h}", flush=True)

                if w < 800 or h < 600:
                    scale_factor = max(800 / w, 600 / h)
                    new_w = int(w * scale_factor)
                    new_h = int(h * scale_factor)
                    rgb_frame = cv2.resize(rgb_frame, (new_w, new_h))
                    print(f"Imagen redimensionada a: {new_w}x{new_h}", flush=True)

                face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                print(f"Face locations encontradas: {len(face_locations)}", flush=True)

                if not face_locations:
                    errores.append(f"Imagen {idx + 1}: No se detecto ningun rostro")
                    continue

                if len(face_locations) > 1:
                    errores.append(f"Imagen {idx + 1}: Se detectaron multiples rostros")
                    continue

                face_encodings_list = face_recognition.face_encodings(rgb_frame, face_locations)
                if face_encodings_list:
                    nuevos_encodings.append(face_encodings_list[0])
                    rostros_procesados += 1
                    print(f"Imagen {idx + 1}: Encoding generado exitosamente", flush=True)

            except Exception as e:
                print(f"Imagen {idx + 1}: EXCEPCION - {str(e)}", flush=True)
                errores.append(f"Imagen {idx + 1}: Error - {str(e)}")
                continue

        if not nuevos_encodings:
            return jsonify({
                'success': False,
                'message': 'No se pudo procesar ninguna imagen valida',
                'errores': errores
            }), 400

        # Reemplazar encodings anteriores de esta persona
        indices_a_eliminar = [i for i, n in enumerate(nombres_conocidos) if n == nombre]
        for indice in reversed(indices_a_eliminar):
            del nombres_conocidos[indice]
            del encodings_conocidos[indice]

        # Promediar nuevos encodings y agregar
        encoding_promedio = np.mean(nuevos_encodings, axis=0)
        nombres_conocidos.append(nombre)
        encodings_conocidos.append(encoding_promedio)

        print(f"{len(nuevos_encodings)} rostro(s) registrado(s) para {nombre}")

        guardar_rostros()

        return jsonify({
            'success': True,
            'message': f'Rostro(s) registrado(s) exitosamente para {nombre}',
            'nombre': nombre,
            'rostros_procesados': rostros_procesados,
            'imagenes_guardadas': len(rutas_guardadas),
            'total_rostros_sistema': len(set(nombres_conocidos)),
            'errores': errores if errores else None
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"Error en /train: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error procesando entrenamiento',
            'error': str(e)
        }), 500


@app.route('/sync', methods=['POST'])
def sync():
    """Recarga encodings desde la DB local de imagenes."""
    try:
        sincronizar_encodings()

        return jsonify({
            'success': True,
            'message': 'Encodings recargados desde DB local',
            'total_rostros': len(nombres_conocidos)
        }), 200

    except Exception as e:
        print(f"Error en /sync: {e}")
        return jsonify({
            'success': False,
            'message': 'Error recargando encodings'
        }), 500


# ==========================================
# RUTAS PARA GESTIONAR LA DB INTERNA
# ==========================================

@app.route('/faces', methods=['GET'])
def listar_faces():
    """Lista todas las personas registradas en la DB interna de imagenes."""
    if not os.path.exists(IMAGENES_DB):
        return jsonify({
            'success': True,
            'personas': [],
            'total': 0
        }), 200

    personas = []
    for d in sorted(os.listdir(IMAGENES_DB)):
        dir_persona = os.path.join(IMAGENES_DB, d)
        if os.path.isdir(dir_persona):
            imagenes = [f for f in os.listdir(dir_persona)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
            en_memoria = d in nombres_conocidos
            personas.append({
                'nombre': d,
                'imagenes': len(imagenes),
                'en_memoria': en_memoria
            })

    return jsonify({
        'success': True,
        'personas': personas,
        'total': len(personas)
    }), 200


@app.route('/faces/<path:nombre>', methods=['GET'])
def obtener_face(nombre):
    """Obtiene info detallada de una persona registrada."""
    dir_persona = os.path.join(IMAGENES_DB, nombre)
    if not os.path.exists(dir_persona):
        return jsonify({
            'success': False,
            'message': f'Persona "{nombre}" no encontrada'
        }), 404

    imagenes = [f for f in os.listdir(dir_persona)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]

    en_memoria = nombre in nombres_conocidos
    idx = nombres_conocidos.index(nombre) if en_memoria else -1
    confianza_promedio = None
    if en_memoria and idx >= 0:
        confianza_promedio = 0.95

    return jsonify({
        'success': True,
        'persona': {
            'nombre': nombre,
            'imagenes': imagenes,
            'total_imagenes': len(imagenes),
            'en_memoria': en_memoria
        }
    }), 200


@app.route('/faces/<path:nombre>', methods=['DELETE'])
def eliminar_face(nombre):
    """Elimina una persona y todas sus imagenes de la DB interna."""
    dir_persona = os.path.join(IMAGENES_DB, nombre)
    if not os.path.exists(dir_persona):
        return jsonify({
            'success': False,
            'message': f'Persona "{nombre}" no encontrada'
        }), 404

    # Eliminar archivos
    import shutil
    shutil.rmtree(dir_persona)
    print(f"Directorio eliminado: {dir_persona}")

    # Eliminar de memoria
    indices = [i for i, n in enumerate(nombres_conocidos) if n == nombre]
    for idx in reversed(indices):
        del nombres_conocidos[idx]
        del encodings_conocidos[idx]

    guardar_rostros()

    return jsonify({
        'success': True,
        'message': f'Persona "{nombre}" eliminada exitosamente'
    }), 200


@app.route('/faces/<path:nombre>/images', methods=['POST'])
def agregar_imagenes_face(nombre):
    """
    Agrega mas imagenes a una persona existente.

    Body (JSON):
    {
        "imagenes": ["data:image/jpeg;base64,...", ...]
    }
    """
    try:
        data = request.get_json()
        if not data or 'imagenes' not in data:
            return jsonify({
                'success': False,
                'message': 'Se requiere un array de imagenes'
            }), 400

        imagenes = data['imagenes']
        if not isinstance(imagenes, list) or not imagenes:
            return jsonify({
                'success': False,
                'message': 'Se requiere al menos una imagen'
            }), 400

        dir_persona = os.path.join(IMAGENES_DB, nombre)
        if not os.path.exists(dir_persona):
            return jsonify({
                'success': False,
                'message': f'Persona "{nombre}" no encontrada. Use /train primero.'
            }), 404

        # Contar imagenes existentes para nombrar las nuevas
        existentes = [f for f in os.listdir(dir_persona)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
        next_idx = len(existentes) + 1

        nuevos_encodings = []
        guardadas = 0
        errores = []

        for idx, imagen_b64 in enumerate(imagenes):
            try:
                frame = imagen_base64_a_array(imagen_b64)
                ruta_img = os.path.join(dir_persona, f"rostro_{next_idx + idx}.jpg")
                cv2.imwrite(ruta_img, frame)

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if rgb_frame.shape[1] < 800 or rgb_frame.shape[0] < 600:
                    scale_factor = max(800 / rgb_frame.shape[1], 600 / rgb_frame.shape[0])
                    rgb_frame = cv2.resize(rgb_frame, (int(rgb_frame.shape[1] * scale_factor),
                                                       int(rgb_frame.shape[0] * scale_factor)))

                face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                if not face_locations:
                    errores.append(f"Imagen {idx + 1}: Sin rostro detectable")
                    continue
                if len(face_locations) > 1:
                    errores.append(f"Imagen {idx + 1}: Multiples rostros")
                    continue

                face_encodings_list = face_recognition.face_encodings(rgb_frame, face_locations)
                if face_encodings_list:
                    nuevos_encodings.append(face_encodings_list[0])
                    guardadas += 1

            except Exception as e:
                errores.append(f"Imagen {idx + 1}: Error - {str(e)}")

        if nuevos_encodings:
            # Recalcular encoding promedio
            indices = [i for i, n in enumerate(nombres_conocidos) if n == nombre]
            for idx in reversed(indices):
                del nombres_conocidos[idx]
                del encodings_conocidos[idx]

            encoding_promedio = np.mean(nuevos_encodings, axis=0)
            nombres_conocidos.append(nombre)
            encodings_conocidos.append(encoding_promedio)
            guardar_rostros()

        return jsonify({
            'success': True,
            'message': f'{guardadas} imagen(es) agregada(s) para {nombre}',
            'imagenes_agregadas': guardadas,
            'errores': errores if errores else None
        }), 200

    except Exception as e:
        print(f"Error agregando imagenes: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/reload', methods=['POST'])
def reload_db():
    """Recarga toda la DB de imagenes desde el disco."""
    try:
        recargar_db()
        return jsonify({
            'success': True,
            'message': 'Base de datos recargada exitosamente',
            'total_personas': len(nombres_conocidos)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==========================================
# INICIAR SERVIDOR
# ==========================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("API de Reconocimiento Facial")
    print("=" * 50)
    print(f"DB interna: {IMAGENES_DB}/")
    print(f"Personas cargadas: {len(nombres_conocidos)}")
    print("=" * 50 + "\n")

    # Asegurar que existe el directorio de la DB
    os.makedirs(IMAGENES_DB, exist_ok=True)

    app.run(
        host='0.0.0.0',
        port=5000,
        threaded=True,
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )
