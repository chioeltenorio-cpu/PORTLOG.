
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import secrets
import hashlib
import os
from datetime import datetime, timedelta, timezone

# -----------------------------------------
# CONFIGURACION DEL MICROSERVICIO AUTH
# -----------------------------------------

app = Flask(__name__)

# Ruta independiente de la base de datos de Auth
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "auth.db")

# Crear la carpeta de datos si aún no existe.
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Roles permitidos para el registro
ROLES = ("agente_aduanal", "transportista")


# -----------------------------------------
# CONEXION A LA BASE DE DATOS
# -----------------------------------------

def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


# -----------------------------------------
# CREACION DE TABLAS
# -----------------------------------------

def inicializar_db():
    with conectar_db() as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                fecha_registro TEXT NOT NULL
            )
        """)

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expiracion TEXT NOT NULL,
                FOREIGN KEY (usuario_id)
                    REFERENCES usuarios(id)
            )
        """)


# -----------------------------------------
# RUTA DE VERIFICACION DEL SERVICIO
# -----------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "servicio": "Auth",
        "estado": "activo",
        "base_datos": "auth.db"
    }), 200


# -----------------------------------------
# REGISTRO DE USUARIOS
# -----------------------------------------

@app.route("/register", methods=["POST"])
def registrar_usuario():

    datos = request.get_json(silent=True) or {}

    nombre = datos.get("nombre", "").strip()
    correo = datos.get("correo", "").strip().lower()
    password = datos.get("password", "")
    rol = datos.get("rol", "")

    if not nombre or not correo or not password or not rol:
        return jsonify({
            "error": "Todos los campos son obligatorios"
        }), 400

    if "@" not in correo or "." not in correo:
        return jsonify({
            "error": "El correo no tiene un formato valido"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "La contraseña debe tener al menos 8 caracteres"
        }), 400

    if rol not in ROLES:
        return jsonify({
            "error": "El rol solicitado no esta permitido"
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with conectar_db() as conexion:

            cursor = conexion.execute("""
                INSERT INTO usuarios
                (nombre, correo, password, rol, fecha_registro)
                VALUES (?, ?, ?, ?, ?)
            """, (
                nombre,
                correo,
                password_hash,
                rol,
                datetime.now(timezone.utc).isoformat()
            ))

            usuario_id = cursor.lastrowid

        return jsonify({
            "mensaje": "Usuario registrado correctamente",
            "usuario": {
                "id": usuario_id,
                "nombre": nombre,
                "correo": correo,
                "rol": rol
            }
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "El correo ya esta registrado"
        }), 409


# -----------------------------------------
# INICIO DE SESION
# -----------------------------------------

@app.route("/login", methods=["POST"])
def iniciar_sesion():

    datos = request.get_json(silent=True) or {}

    correo = datos.get("correo", "").strip().lower()
    password = datos.get("password", "")

    if not correo or not password:
        return jsonify({
            "error": "Correo y contraseña son obligatorios"
        }), 400

    with conectar_db() as conexion:

        usuario = conexion.execute("""
            SELECT * FROM usuarios
            WHERE correo = ?
        """, (correo,)).fetchone()

        if usuario is None or not check_password_hash(
            usuario["password"], password
        ):
            return jsonify({
                "error": "Credenciales incorrectas"
            }), 401

        # Generar token de acceso
        token = secrets.token_urlsafe(32)

        # Guardar solamente el hash del token
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        expiracion = (
            datetime.now(timezone.utc) + timedelta(hours=8)
        ).isoformat()

        conexion.execute("""
            INSERT INTO sesiones
            (usuario_id, token_hash, expiracion)
            VALUES (?, ?, ?)
        """, (
            usuario["id"],
            token_hash,
            expiracion
        ))

    return jsonify({
        "mensaje": "Inicio de sesion exitoso",
        "token": token,
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "correo": usuario["correo"],
            "rol": usuario["rol"]
        }
    }), 200


# -----------------------------------------
# CONSULTAR USUARIO AUTENTICADO
# -----------------------------------------

@app.route("/me", methods=["GET"])
def consultar_usuario():

    autorizacion = request.headers.get("Authorization", "")

    if not autorizacion.startswith("Bearer "):
        return jsonify({
            "error": "Token de acceso requerido"
        }), 401

    token = autorizacion.split(" ", 1)[1]

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    with conectar_db() as conexion:

        sesion = conexion.execute("""
            SELECT usuarios.id, usuarios.nombre,
                   usuarios.correo, usuarios.rol,
                   sesiones.expiracion
            FROM sesiones
            JOIN usuarios
            ON sesiones.usuario_id = usuarios.id
            WHERE sesiones.token_hash = ?
        """, (token_hash,)).fetchone()

        if sesion is None:
            return jsonify({
                "error": "Sesion no valida"
            }), 401

        expiracion = datetime.fromisoformat(
            sesion["expiracion"]
        )

        if datetime.now(timezone.utc) >= expiracion:
            conexion.execute("""
                DELETE FROM sesiones
                WHERE token_hash = ?
            """, (token_hash,))

            return jsonify({
                "error": "La sesion ha expirado"
            }), 401

    return jsonify({
        "autenticado": True,
        "usuario": {
            "id": sesion["id"],
            "nombre": sesion["nombre"],
            "correo": sesion["correo"],
            "rol": sesion["rol"]
        }
    }), 200


# -----------------------------------------
# CERRAR SESION
# -----------------------------------------

@app.route("/logout", methods=["POST"])
def cerrar_sesion():

    autorizacion = request.headers.get("Authorization", "")

    if not autorizacion.startswith("Bearer "):
        return jsonify({
            "error": "Token de acceso requerido"
        }), 401

    token = autorizacion.split(" ", 1)[1]

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    with conectar_db() as conexion:

        cursor = conexion.execute("""
            DELETE FROM sesiones
            WHERE token_hash = ?
        """, (token_hash,))

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Sesion no encontrada"
            }), 404

    return jsonify({
        "mensaje": "Sesion cerrada correctamente"
    }), 200


# -----------------------------------------
# INICIAR MICROSERVICIO
# -----------------------------------------

if __name__ == "__main__":

    inicializar_db()

    print("===================================")
    print(" MICROSERVICIO AUTH - PORTLOG")
    print(" Servidor: http://127.0.0.1:5001")
    print("===================================")

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False
    )
