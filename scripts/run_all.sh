#!/bin/bash
#
# clockControl - Ejecutar modo masivo
# Obtiene marcajes de TODOS los relojes activos en la base de datos
#
# Uso: ./run_all.sh
#

set -e

# Obtener directorio del script
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

# Ejecutar clockControl modo masivo
python -m clockcontrol all

# Log de ejecucion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Ejecutado modo masivo" >> "$SCRIPT_DIR/clockcontrol.log"
