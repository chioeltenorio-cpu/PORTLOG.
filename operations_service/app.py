
from flask import Flask, request, jsonify
import sqlite3
import os
import requests
from datetime import datetime, timezone

# -----------------------------------------
# CONFIGURACION DEL MICROSERVICIO
# -----------------------------------------

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "operations.db")

# Crear la carpeta de datos si aún no existe.
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

INVENTORY_URL = "http://127.0.0.1:5002"

TIPOS_OPERACION = (
    "entrada",
    "salida",
    "liberacion_aduanal"
)


# -----------------------------------------
# CONEXION A BASE DE DATOS PROPIA
# -----------------------------------------

def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


# -----------------------------------------
# CREAR TABLA DE MOVIMIENTOS
# -----------------------------------------

def inicializar_db():

    with conectar_db() as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_contenedor TEXT NOT NULL,
                tipo_operacion TEXT NOT NULL,
                observaciones TEXT,
                fecha TEXT NOT NULL
            )
        """)


# -----------------------------------------
# COMUNICACION HTTP CON INVENTARIO
# -----------------------------------------

def consultar_inventario(numero):

    try:
        respuesta = requests.get(
            f"{INVENTORY_URL}/containers/{numero}",
            timeout=3
        )

        if respuesta.status_code == 404:
            return None, "Contenedor no encontrado", 404

        if respuesta.status_code != 200:
            return None, "Error al consultar Inventario", 502

        return respuesta.json().get("contenedor"), None, None

    except requests.exceptions.Timeout:
        return None, "Inventario no respondio a tiempo", 503

    except requests.exceptions.ConnectionError:
        return None, "Microservicio Inventario no disponible", 503


# -----------------------------------------
# VERIFICAR ESTADO DEL SERVICIO
# -----------------------------------------

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "servicio": "Operaciones",
        "estado": "activo",
        "base_datos": "operations.db"
    }), 200


# -----------------------------------------
# REGISTRAR UN MOVIMIENTO
# -----------------------------------------

@app.route("/movements", methods=["POST"])
def registrar_movimiento():

    datos = request.get_json(silent=True) or {}

    numero = str(datos.get("numero", "")).strip().upper()
    tipo = str(datos.get("tipo_operacion", "")).strip().lower()
    observaciones = str(datos.get("observaciones", "")).strip()

    if not numero or not tipo:
        return jsonify({
            "error": "Numero y tipo de operacion son obligatorios"
        }), 400

    if tipo not in TIPOS_OPERACION:
        return jsonify({
            "error": "Tipo de operacion no valido",
            "tipos_validos": TIPOS_OPERACION
        }), 400

    # Consultar el microservicio Inventario por HTTP

    contenedor, error, codigo = consultar_inventario(numero)

    if error:
        return jsonify({
            "error": error
        }), codigo

    # Consultar el ultimo movimiento registrado

    with conectar_db() as conexion:

        ultimo = conexion.execute("""
            SELECT * FROM movimientos
            WHERE numero_contenedor = ?
            ORDER BY id DESC
            LIMIT 1
        """, (numero,)).fetchone()

        ultimo_tipo = ultimo["tipo_operacion"] if ultimo else None

        # Validacion de entradas y salidas

        if tipo == "entrada" and ultimo_tipo == "entrada":
            return jsonify({
                "error": "El contenedor ya tiene una entrada registrada"
            }), 409

        if tipo == "salida" and ultimo_tipo != "entrada":
            return jsonify({
                "error": "No se puede registrar una salida sin una entrada previa"
            }), 409

        if tipo == "liberacion_aduanal" and ultimo_tipo == "liberacion_aduanal":
            return jsonify({
                "error": "La liberacion aduanal ya fue registrada"
            }), 409

        fecha = datetime.now(timezone.utc).isoformat()

        cursor = conexion.execute("""
            INSERT INTO movimientos (
                numero_contenedor,
                tipo_operacion,
                observaciones,
                fecha
            )
            VALUES (?, ?, ?, ?)
        """, (
            numero,
            tipo,
            observaciones,
            fecha
        ))

        movimiento = conexion.execute("""
            SELECT * FROM movimientos WHERE id = ?
        """, (cursor.lastrowid,)).fetchone()

    return jsonify({
        "mensaje": "Movimiento registrado correctamente",
        "contenedor": {
            "numero": contenedor["numero"],
            "descripcion": contenedor["descripcion"]
        },
        "movimiento": {
            "id": movimiento["id"],
            "tipo_operacion": movimiento["tipo_operacion"],
            "observaciones": movimiento["observaciones"],
            "fecha": movimiento["fecha"]
        }
    }), 201


# -----------------------------------------
# CONSULTAR TODOS LOS MOVIMIENTOS
# -----------------------------------------

@app.route("/movements", methods=["GET"])
def listar_movimientos():

    numero = request.args.get("numero", "").strip().upper()

    with conectar_db() as conexion:

        if numero:
            registros = conexion.execute("""
                SELECT * FROM movimientos
                WHERE numero_contenedor = ?
                ORDER BY id DESC
            """, (numero,)).fetchall()

        else:
            registros = conexion.execute("""
                SELECT * FROM movimientos
                ORDER BY id DESC
            """).fetchall()

    movimientos = []

    for registro in registros:
        movimientos.append({
            "id": registro["id"],
            "numero_contenedor": registro["numero_contenedor"],
            "tipo_operacion": registro["tipo_operacion"],
            "observaciones": registro["observaciones"],
            "fecha": registro["fecha"]
        })

    return jsonify({
        "total": len(movimientos),
        "movimientos": movimientos
    }), 200


# -----------------------------------------
# CONSULTAR ESTADO OPERATIVO
# -----------------------------------------

@app.route("/containers/<numero>/status", methods=["GET"])
def consultar_estado(numero):

    numero = numero.upper()

    contenedor, error, codigo = consultar_inventario(numero)

    if error:
        return jsonify({"error": error}), codigo

    with conectar_db() as conexion:

        ultimo = conexion.execute("""
            SELECT * FROM movimientos
            WHERE numero_contenedor = ?
            ORDER BY id DESC
            LIMIT 1
        """, (numero,)).fetchone()

    if ultimo is None:
        estado = "sin_movimientos"

    elif ultimo["tipo_operacion"] == "entrada":
        estado = "dentro_del_puerto"

    elif ultimo["tipo_operacion"] == "salida":
        estado = "fuera_del_puerto"

    else:
        estado = "liberado_aduanalmente"

    return jsonify({
        "numero_contenedor": numero,
        "descripcion": contenedor["descripcion"],
        "estado_operativo": estado,
        "ultimo_movimiento": (
            ultimo["tipo_operacion"] if ultimo else None
        )
    }), 200


# -----------------------------------------
# INICIAR MICROSERVICIO
# -----------------------------------------

if __name__ == "__main__":

    inicializar_db()

    print("===================================")
    print(" MICROSERVICIO OPERACIONES - PORTLOG")
    print(" Servidor: http://127.0.0.1:5003")
    print("===================================")

    app.run(
        host="127.0.0.1",
        port=5003,
        debug=False
    )