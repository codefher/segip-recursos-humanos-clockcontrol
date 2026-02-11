#!/bin/bash
#
# clockControl - Ejecutar modo individual
# Uso: ./run_single.sh <IP> [PORT] [PASSWORD]
#
# Ejemplo: ./run_single.sh 192.168.1.201 4370 0
#

set -e

# Validar argumentos
if [ "$#" -lt 1 ]; then
    echo "Uso: $0 <IP> [PORT] [PASSWORD]"
    echo "Ejemplo: $0 192.168.1.201 4370 0"
    exit 1
fi

# Obtener parametros
IP="$1"
PORT="${2:-4370}"
PASSWORD="${3:-0}"

# Obtener directorio del script (funciona desde cualquier ubicacion)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

# Ir al directorio principal
cd "$SCRIPT_DIR"

# Activar entorno virtual
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
else
    echo "Error: No se encontro el entorno virtual en $SCRIPT_DIR/venv"
    echo "Ejecute: python3 -m venv venv && pip install -e ."
    exit 1
fi

# Ejecutar clockControl modo individual
python -m clockcontrol single --address "$IP" --port "$PORT" --password "$PASSWORD"

# Log de ejecucion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Ejecutado modo individual: $IP:$PORT" >> "$SCRIPT_DIR/clockcontrol.log"
