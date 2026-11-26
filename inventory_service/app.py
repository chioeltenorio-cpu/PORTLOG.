
from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime, timezone

# -----------------------------------------
# CONFIGURACION DEL MICROSERVICIO INVENTARIO
# -----------------------------------------

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "inventory.db")

# Crear la carpeta de datos si aún no existe.
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

TIPOS_CONTENEDOR = (
    "seco",
    "refrigerado",
    "tanque",
    "especial"
)


# -----------------------------------------
# CONEXION A SU PROPIA BASE DE DATOS
# -----------------------------------------

def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


# -----------------------------------------
# CREACION DE LA TABLA DE CONTENEDORES
# -----------------------------------------

def inicializar_db():

    with conectar_db() as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS contenedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL UNIQUE,
                descripcion TEXT NOT NULL,
                tipo TEXT NOT NULL,
                peso_kg REAL NOT NULL,
                transportista TEXT NOT NULL,
                origen TEXT NOT NULL,
                destino TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'registrado',
                fecha_registro TEXT NOT NULL
            )
        """)


# -----------------------------------------
# CONVERTIR REGISTRO A JSON
# -----------------------------------------

def convertir_contenedor(registro):
    return {
        "id": registro["id"],
        "numero": registro["numero"],
        "descripcion": registro["descripcion"],
        "tipo": registro["tipo"],
        "peso_kg": registro["peso_kg"],
        "transportista": registro["transportista"],
        "origen": registro["origen"],
        "destino": registro["destino"],
        "estado": registro["estado"],
        "fecha_registro": registro["fecha_registro"]
    }


# -----------------------------------------
# VERIFICAR ESTADO DEL SERVICIO
# -----------------------------------------

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "servicio": "Inventario",
        "estado": "activo",
        "base_datos": "inventory.db"
    }), 200


# -----------------------------------------
# REGISTRAR UN CONTENEDOR
# -----------------------------------------

@app.route("/containers", methods=["POST"])
def registrar_contenedor():

    datos = request.get_json(silent=True) or {}

    campos = [
        "numero",
        "descripcion",
        "tipo",
        "peso_kg",
        "transportista",
        "origen",
        "destino"
    ]

    for campo in campos:
        if campo not in datos:
            return jsonify({
                "error": f"El campo {campo} es obligatorio"
            }), 400

    numero = str(datos["numero"]).strip().upper()
    descripcion = str(datos["descripcion"]).strip()
    tipo = str(datos["tipo"]).strip().lower()
    transportista = str(datos["transportista"]).strip()
    origen = str(datos["origen"]).strip()
    destino = str(datos["destino"]).strip()

    try:
        peso = float(datos["peso_kg"])
    except (ValueError, TypeError):
        return jsonify({
            "error": "El peso debe ser un valor numerico"
        }), 400

    if not all([
        numero, descripcion, transportista, origen, destino
    ]):
        return jsonify({
            "error": "Los campos de texto no pueden estar vacios"
        }), 400

    if len(numero) > 20:
        return jsonify({
            "error": "El numero de contenedor es demasiado largo"
        }), 400

    if tipo not in TIPOS_CONTENEDOR:
        return jsonify({
            "error": "Tipo de contenedor no permitido",
            "tipos_validos": TIPOS_CONTENEDOR
        }), 400

    if peso <= 0:
        return jsonify({
            "error": "El peso debe ser mayor que cero"
        }), 400

    fecha = datetime.now(timezone.utc).isoformat()

    try:
        with conectar_db() as conexion:

            cursor = conexion.execute("""
                INSERT INTO contenedores (
                    numero, descripcion, tipo, peso_kg,
                    transportista, origen, destino,
                    estado, fecha_registro
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                numero,
                descripcion,
                tipo,
                peso,
                transportista,
                origen,
                destino,
                "registrado",
                fecha
            ))

            nuevo = conexion.execute("""
                SELECT * FROM contenedores WHERE id = ?
            """, (cursor.lastrowid,)).fetchone()

        return jsonify({
            "mensaje": "Contenedor registrado correctamente",
            "contenedor": convertir_contenedor(nuevo)
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "El numero de contenedor ya existe"
        }), 409


# -----------------------------------------
# CONSULTAR TODOS LOS CONTENEDORES
# -----------------------------------------

@app.route("/containers", methods=["GET"])
def listar_contenedores():

    with conectar_db() as conexion:

        registros = conexion.execute("""
            SELECT * FROM contenedores
            ORDER BY id DESC
        """).fetchall()

    return jsonify({
        "total": len(registros),
        "contenedores": [
            convertir_contenedor(registro)
            for registro in registros
        ]
    }), 200


# -----------------------------------------
# BUSCAR CONTENEDOR POR NUMERO
# -----------------------------------------

@app.route("/containers/<numero>", methods=["GET"])
def buscar_contenedor(numero):

    with conectar_db() as conexion:

        registro = conexion.execute("""
            SELECT * FROM contenedores
            WHERE numero = ?
        """, (numero.upper(),)).fetchone()

    if registro is None:
        return jsonify({
            "error": "Contenedor no encontrado"
        }), 404

    return jsonify({
        "contenedor": convertir_contenedor(registro)
    }), 200


# -----------------------------------------
# ACTUALIZAR DATOS DEL CONTENEDOR
# -----------------------------------------

@app.route("/containers/<numero>", methods=["PUT"])
def actualizar_contenedor(numero):

    datos = request.get_json(silent=True) or {}

    campos_permitidos = {
        "descripcion",
        "tipo",
        "peso_kg",
        "transportista",
        "origen",
        "destino"
    }

    if not datos:
        return jsonify({
            "error": "No se recibieron datos para actualizar"
        }), 400

    if not set(datos.keys()).issubset(campos_permitidos):
        return jsonify({
            "error": "Se enviaron campos no permitidos"
        }), 400

    valores = {}

    for campo, valor in datos.items():

        if campo == "peso_kg":
            try:
                peso = float(valor)
            except (ValueError, TypeError):
                return jsonify({
                    "error": "El peso debe ser numerico"
                }), 400

            if peso <= 0:
                return jsonify({
                    "error": "El peso debe ser mayor que cero"
                }), 400

            valores[campo] = peso

        elif campo == "tipo":
            tipo = str(valor).strip().lower()

            if tipo not in TIPOS_CONTENEDOR:
                return jsonify({
                    "error": "Tipo de contenedor no permitido"
                }), 400

            valores[campo] = tipo

        else:
            texto = str(valor).strip()

            if not texto:
                return jsonify({
                    "error": f"El campo {campo} no puede estar vacio"
                }), 400

            valores[campo] = texto

    columnas = ", ".join(
        f"{campo} = ?" for campo in valores
    )

    parametros = list(valores.values()) + [numero.upper()]

    with conectar_db() as conexion:

        cursor = conexion.execute(
            f"UPDATE contenedores SET {columnas} WHERE numero = ?",
            parametros
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Contenedor no encontrado"
            }), 404

        actualizado = conexion.execute("""
            SELECT * FROM contenedores WHERE numero = ?
        """, (numero.upper(),)).fetchone()

    return jsonify({
        "mensaje": "Contenedor actualizado correctamente",
        "contenedor": convertir_contenedor(actualizado)
    }), 200


# -----------------------------------------
# INICIAR MICROSERVICIO
# -----------------------------------------

if __name__ == "__main__":

    inicializar_db()

    print("===================================")
    print(" MICROSERVICIO INVENTARIO - PORTLOG")
    print(" Servidor: http://127.0.0.1:5002")
    print("===================================")

    app.run(
        host="127.0.0.1",
        port=5002,
        debug=False
    )
