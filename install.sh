#!/bin/bash
#
# clockControl - Script de Instalación
# Sistema de Control de Asistencia SEGIP
#

set -e  # Detener si hay error

echo "======================================"
echo "clockControl - Instalación"
echo "======================================"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detectar directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📂 Directorio de instalación: $SCRIPT_DIR"
echo ""

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 no está instalado${NC}"
    echo "Instalar con: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python encontrado: $PYTHON_VERSION"

# Verificar pip
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}❌ Error: pip no está instalado${NC}"
    echo "Instalar con: sudo apt install python3-pip"
    exit 1
fi

echo -e "${GREEN}✓${NC} pip está instalado"

# Crear entorno virtual
echo ""
echo "🔧 Creando entorno virtual..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠${NC}  Entorno virtual ya existe. Eliminando..."
    rm -rf venv
fi

python3 -m venv venv
echo -e "${GREEN}✓${NC} Entorno virtual creado"

# Activar entorno virtual
echo ""
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo ""
echo "🔧 Actualizando pip..."
python -m pip install --upgrade pip --quiet

# Instalar dependencias
echo ""
echo "🔧 Instalando dependencias..."
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt no encontrado${NC}"
    exit 1
fi

pip install -r requirements.txt

echo -e "${GREEN}✓${NC} Dependencias instaladas"

# Verificar instalación de dependencias críticas
echo ""
echo "🔍 Verificando dependencias críticas..."
python -c "import psycopg2" && echo -e "${GREEN}✓${NC} psycopg2 OK" || echo -e "${RED}❌ psycopg2 FALLO${NC}"
python -c "from zk import ZK" && echo -e "${GREEN}✓${NC} pyzk OK" || echo -e "${YELLOW}⚠${NC}  pyzk no disponible (instalar manualmente si es necesario)"

# Configurar base de datos
echo ""
echo "🔧 Configurando base de datos..."
if [ ! -f "database.ini" ]; then
    if [ -f "tmp.database.ini" ]; then
        cp tmp.database.ini database.ini
        echo -e "${YELLOW}⚠${NC}  Archivo database.ini creado desde template"
        echo -e "${YELLOW}⚠${NC}  IMPORTANTE: Editar database.ini con las credenciales correctas"
        echo ""
        echo "Editar con: nano database.ini"
    else
        echo -e "${RED}❌ Error: tmp.database.ini no encontrado${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} database.ini ya existe"
fi

# Dar permisos a scripts
echo ""
echo "🔧 Configurando permisos de scripts..."
chmod +x scripts/*.sh 2>/dev/null || true
echo -e "${GREEN}✓${NC} Permisos configurados"

# Crear carpetas necesarias
echo ""
echo "🔧 Verificando estructura de carpetas..."
mkdir -p src tests scripts sql/migrations
echo -e "${GREEN}✓${NC} Estructura verificada"

# Resumen
echo ""
echo "======================================"
echo -e "${GREEN}✅ Instalación completada${NC}"
echo "======================================"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Configurar base de datos:"
echo "   nano database.ini"
echo ""
echo "2. Activar entorno virtual:"
echo "   source venv/bin/activate"
echo ""
echo "3. Ejecutar modo individual:"
echo "   ./scripts/run_single_v2.sh <IP> [PORT] [PASSWORD]"
echo ""
echo "4. Ejecutar modo masivo:"
echo "   ./scripts/run_all_v2.sh"
echo ""
echo "5. Ejecutar tests:"
echo "   python tests/test_attendance.py"
echo ""
echo "======================================"
