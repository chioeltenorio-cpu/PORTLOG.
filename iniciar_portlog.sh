
#!/bin/bash

# ==========================================
# PORTLOG - INICIO AUTOMATICO
# ==========================================

cd "$(dirname "$0")" || exit 1

echo "======================================"
echo "       PORTLOG - INICIANDO SISTEMA"
echo "======================================"

source venv/bin/activate || exit 1

# Funcion para detener los servicios iniciados
detener_servicios() {
    echo ""
    echo "Deteniendo PORTLOG..."

    for pid in "$FRONTEND_PID" "$GATEWAY_PID" \
               "$OPERATIONS_PID" "$INVENTORY_PID" "$AUTH_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
        fi
    done

    echo "PORTLOG detenido."
    exit 0
}

trap detener_servicios INT TERM

# Iniciar Auth
python auth_service/app.py &
AUTH_PID=$!
sleep 2

# Iniciar Inventory
python inventory_service/app.py &
INVENTORY_PID=$!
sleep 2

# Iniciar Operations
python operations_service/app.py &
OPERATIONS_PID=$!
sleep 2

# Iniciar Gateway
python api_gateway/app.py &
GATEWAY_PID=$!
sleep 2

# Iniciar Frontend
cd frontend || exit 1
python -m http.server 5500 &
FRONTEND_PID=$!

echo ""
echo "PORTLOG iniciado correctamente."
echo "Frontend: http://127.0.0.1:5500"
echo "Gateway:  http://127.0.0.1:5000/health"
echo ""
echo "Presiona Ctrl+C para detener PORTLOG."

wait
