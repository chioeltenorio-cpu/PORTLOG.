#!/bin/bash

# ==========================================
# PORTLOG - INICIO AUTOMATICO
# Compatible con macOS y Linux
# ==========================================

set -u

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR" || exit 1

echo "======================================"
echo "       PORTLOG - INICIANDO SISTEMA"
echo "======================================"

# Verificar Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 no está instalado o no está disponible en PATH."
    exit 1
fi

# Verificar archivo de dependencias
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: No se encontró requirements.txt en la carpeta PORTLOG."
    exit 1
fi

# Crear el entorno virtual en la primera ejecución.
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv || exit 1
    echo "Instalando dependencias..."
    ./venv/bin/python -m pip install -r requirements.txt || exit 1
fi

# Activar el entorno virtual existente o recién creado.
source venv/bin/activate || exit 1

# Crear las carpetas de datos. SQLite creará los archivos .db al inicializar
# las tablas de cada microservicio.
mkdir -p auth_service/data inventory_service/data operations_service/data

# Detener únicamente los procesos iniciados por este script.
detener_servicios() {
    echo ""
    echo "Deteniendo PORTLOG..."
    for pid in "$FRONTEND_PID" "$GATEWAY_PID" \
               "$OPERATIONS_PID" "$INVENTORY_PID" "$AUTH_PID"; do
        if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
        fi
    done
    echo "PORTLOG detenido."
    exit 0
}

# Esperar a que un endpoint responda antes de continuar.
esperar_servicio() {
    nombre="$1"
    url="$2"
    intentos=20

    echo "Comprobando $nombre..."
    while [ "$intentos" -gt 0 ]; do
        if curl -fsS "$url" >/dev/null 2>&1; then
            echo "$nombre disponible: $url"
            return 0
        fi
        sleep 1
        intentos=$((intentos - 1))
    done

    echo "ERROR: $nombre no respondió en el tiempo esperado ($url)."
    return 1
}

AUTH_PID=""
INVENTORY_PID=""
OPERATIONS_PID=""
GATEWAY_PID=""
FRONTEND_PID=""

trap detener_servicios INT TERM

# Iniciar Auth
echo "Iniciando Auth..."
python auth_service/app.py &
AUTH_PID=$!
esperar_servicio "Auth" "http://127.0.0.1:5001/health" || detener_servicios

# Iniciar Inventory
echo "Iniciando Inventory..."
python inventory_service/app.py &
INVENTORY_PID=$!
esperar_servicio "Inventory" "http://127.0.0.1:5002/health" || detener_servicios

# Iniciar Operations
echo "Iniciando Operations..."
python operations_service/app.py &
OPERATIONS_PID=$!
esperar_servicio "Operations" "http://127.0.0.1:5003/health" || detener_servicios

# Iniciar API Gateway
echo "Iniciando API Gateway..."
python api_gateway/app.py &
GATEWAY_PID=$!
esperar_servicio "API Gateway" "http://127.0.0.1:5000/health" || detener_servicios

# Iniciar Frontend
echo "Iniciando Frontend..."
cd "$ROOT_DIR/frontend" || detener_servicios
python -m http.server 5500 &
FRONTEND_PID=$!
esperar_servicio "Frontend" "http://127.0.0.1:5500/" || detener_servicios

echo ""
echo "======================================"
echo "       PORTLOG INICIADO"
echo "======================================"
echo "Frontend: http://127.0.0.1:5500"
echo "Gateway:  http://127.0.0.1:5000/health"
echo "Auth:     http://127.0.0.1:5001/health"
echo "Inventory:http://127.0.0.1:5002/health"
echo "Operations:http://127.0.0.1:5003/health"
echo ""
echo "Presiona Ctrl+C para detener PORTLOG."

wait
