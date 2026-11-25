
from flask import Flask, request, Response, jsonify
import requests

app = Flask(__name__)

# ==========================================
# CONFIGURACION DE LOS MICROSERVICIOS
# ==========================================

SERVICIOS = {
    "auth": "http://127.0.0.1:5001",
    "inventory": "http://127.0.0.1:5002",
    "operations": "http://127.0.0.1:5003"
}

# ==========================================
# CONFIGURACION CORS
# ==========================================

@app.after_request
def configurar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization"
    )
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, DELETE, OPTIONS"
    )
    return response


# ==========================================
# ESTADO DEL API GATEWAY
# ==========================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "servicio": "API Gateway - PORTLOG",
        "estado": "activo",
        "puerto": 5000
    }), 200


# ==========================================
# VALIDAR TOKEN CON AUTH
# ==========================================

def validar_token():

    autorizacion = request.headers.get("Authorization", "")

    if not autorizacion.startswith("Bearer "):
        return None, (jsonify({
            "error": "Token de autenticacion requerido"
        }), 401)

    try:
        respuesta = requests.get(
            f"{SERVICIOS['auth']}/me",
            headers={
                "Authorization": autorizacion
            },
            timeout=3
        )

        if respuesta.status_code == 401:
            return None, (jsonify({
                "error": "Sesion no valida o expirada"
            }), 401)

        if respuesta.status_code != 200:
            return None, (jsonify({
                "error": "No fue posible validar la sesion"
            }), 502)

        datos = respuesta.json()

        if datos.get("autenticado") is False:
            return None, (jsonify({
                "error": "Usuario no autenticado"
            }), 401)

        usuario = datos.get("usuario", datos)
        rol = usuario.get("rol")

        if not rol:
            return None, (jsonify({
                "error": "No se pudo identificar el rol del usuario"
            }), 403)

        return {
            "id": usuario.get("id"),
            "nombre": usuario.get("nombre"),
            "correo": usuario.get("correo"),
            "rol": rol
        }, None

    except requests.exceptions.Timeout:
        return None, (jsonify({
            "error": "Tiempo de espera al validar el usuario"
        }), 504)

    except requests.exceptions.ConnectionError:
        return None, (jsonify({
            "error": "El servicio Auth no esta disponible"
        }), 503)

    except (requests.exceptions.RequestException, ValueError):
        return None, (jsonify({
            "error": "Error al comunicarse con Auth"
        }), 502)


# ==========================================
# VERIFICAR PERMISOS SEGUN ROL
# ==========================================

def verificar_permisos(servicio, path, metodo, rol, datos=None):

    ruta = "/" + path.strip("/")
    datos = datos or {}

    if servicio == "inventory":

        if metodo == "GET" and (
            ruta == "/containers" or
            ruta.startswith("/containers/")
        ):
            return rol in ["agente_aduanal", "transportista"]

        if metodo == "POST" and ruta == "/containers":
            return rol == "agente_aduanal"

        if metodo == "PUT" and ruta.startswith("/containers/"):
            return rol == "agente_aduanal"

        return False

    if servicio == "operations":

        if metodo == "GET" and (
            ruta == "/movements" or
            ruta.endswith("/status")
        ):
            return rol in ["agente_aduanal", "transportista"]

        if metodo == "POST" and ruta == "/movements":

            tipo = datos.get("tipo_operacion")

            if rol == "transportista":
                return tipo in ["entrada", "salida"]

            if rol == "agente_aduanal":
                return tipo == "liberacion_aduanal"

        return False

    return False
    
    # --------------------------------------
    # PERMISOS DE INVENTARIO
    # --------------------------------------

    if servicio == "inventory":

        # Ambos roles pueden consultar contenedores
        if metodo == "GET" and (
            ruta == "/containers" or
            ruta.startswith("/containers/")
        ):
            return rol in [
                "agente_aduanal",
                "transportista"
            ]

        # Solo agente aduanal puede registrar
        if metodo == "POST" and ruta == "/containers":
            return rol == "agente_aduanal"

        # Solo agente aduanal puede editar
        if metodo == "PUT" and ruta.startswith("/containers/"):
            return rol == "agente_aduanal"

        return False

    # --------------------------------------
    # PERMISOS DE OPERACIONES
    # --------------------------------------

    if servicio == "operations":

        # Ambos roles pueden consultar movimientos
        if metodo == "GET" and ruta == "/movements":
            return rol in [
                "agente_aduanal",
                "transportista"
            ]

        # Transportista registra entradas y salidas
        if metodo == "POST" and ruta == "/movements":
            return rol == "transportista"

        # Ambos pueden consultar el estado del contenedor
        if metodo == "GET" and ruta.endswith("/status"):
            return rol in [
                "agente_aduanal",
                "transportista"
            ]

        return False

    return False


# ==========================================
# FUNCION PRINCIPAL DE ENRUTAMIENTO
# ==========================================

def redirigir_peticion(servicio, path):

    if servicio not in SERVICIOS:
        return jsonify({
            "error": "Microservicio no encontrado"
        }), 404

    # Responder solicitudes OPTIONS sin autenticacion
    if request.method == "OPTIONS":
        return Response(status=204)

    # --------------------------------------
    # AUTENTICACION Y AUTORIZACION
    # --------------------------------------

    if servicio in ["inventory", "operations"]:

        usuario, error = validar_token()

        if error:
            return error

        permitido = verificar_permisos(
    servicio,
    path,
    request.method,
    usuario["rol"],
    request.get_json(silent=True) or {}
)
        

        if not permitido:
            return jsonify({
                "error": "No tienes permisos para realizar esta operacion",
                "rol": usuario["rol"],
                "servicio": servicio
            }), 403

    # --------------------------------------
    # REENVIAR PETICION AL MICROSERVICIO
    # --------------------------------------

    url = f"{SERVICIOS[servicio]}/{path}"

    headers = {
        key: value
        for key, value in request.headers
        if key.lower() not in [
            "host",
            "content-length",
            "connection"
        ]
    }

    try:
        respuesta = requests.request(
            method=request.method,
            url=url,
            params=request.args,
            data=request.get_data(),
            headers=headers,
            timeout=5,
            allow_redirects=False
        )

        return Response(
            respuesta.content,
            status=respuesta.status_code,
            content_type=respuesta.headers.get(
                "Content-Type",
                "application/json"
            )
        )

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Tiempo de espera agotado",
            "servicio": servicio
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Microservicio no disponible",
            "servicio": servicio,
            "mensaje": "El Gateway sigue funcionando"
        }), 503

    except requests.exceptions.RequestException:
        return jsonify({
            "error": "Error en la comunicacion con el microservicio"
        }), 502


# ==========================================
# RUTAS DEL API GATEWAY
# ==========================================

@app.route(
    "/api/<servicio>/",
    defaults={"path": ""},
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
@app.route(
    "/api/<servicio>/<path:path>",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
def gateway(servicio, path):
    return redirigir_peticion(servicio, path)


# ==========================================
# INICIAR API GATEWAY
# ==========================================

if __name__ == "__main__":

    print("======================================")
    print("       PORTLOG - API GATEWAY")
    print("======================================")
    print("Servidor: http://127.0.0.1:5000")
    print("Auth:       Puerto 5001")
    print("Inventario: Puerto 5002")
    print("Operaciones: Puerto 5003")
    print("Seguridad: Autenticacion y roles activos")
    print("======================================")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
