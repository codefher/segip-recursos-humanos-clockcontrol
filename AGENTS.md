# AGENTS.md - clockControl v2.0

> Guia para agentes de codigo (Claude, Copilot, Cursor, etc.) que trabajan en este repositorio.

## Descripcion del Proyecto

**clockControl** es un sistema de control de asistencia para SEGIP (Bolivia) que:
- Se conecta a relojes biometricos ZKTeco via protocolo UDP/TCP
- Extrae marcajes de asistencia de los dispositivos
- Almacena los datos en PostgreSQL (esquema `rrhh`)
- Se ejecuta via cron cada 5 minutos

## Stack Tecnologico

| Componente | Tecnologia |
|------------|------------|
| Lenguaje | Python 3.9+ |
| Base de Datos | PostgreSQL 12+ |
| Comunicacion ZK | pyzk (biblioteca) |
| SO Target | Linux Debian 12 |
| Orquestacion | Cron + Bash Scripts |
| Packaging | pyproject.toml (PEP 517/518) |

## Estructura del Proyecto

```
clockcontrol/
├── clockcontrol/                  # Paquete principal Python
│   ├── __init__.py               # API publica del paquete
│   ├── __main__.py               # Entry point: python -m clockcontrol
│   ├── cli.py                    # CLI y ClockControlApp
│   ├── core/                     # Logica de negocio
│   │   ├── __init__.py
│   │   ├── attendance.py         # AttendanceProcessor, AttendanceMark
│   │   ├── device.py             # ZKDeviceManager
│   │   └── exceptions.py         # Excepciones personalizadas
│   ├── database/                 # Capa de acceso a datos
│   │   ├── __init__.py
│   │   ├── connection.py         # DatabaseConnection
│   │   ├── models.py             # Clock, ConnectionLog
│   │   └── repositories.py       # ClockRepository, AttendanceRepository
│   ├── config/                   # Configuracion
│   │   ├── __init__.py
│   │   └── settings.py           # Settings, DatabaseConfig, get_settings()
│   └── utils/
│       └── __init__.py
├── scripts/                       # Scripts bash para cron
│   ├── run_single.sh             # Ejecutar modo individual
│   └── run_all.sh                # Ejecutar modo masivo
├── tests/                         # Tests con pytest
│   ├── __init__.py
│   ├── test_attendance.py        # Tests de AttendanceProcessor
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── sql/
│   └── stored_procedures/        # Stored procedures PostgreSQL
├── pyproject.toml                # Configuracion del proyecto (PEP 517)
├── requirements.txt              # Dependencias (3 paquetes)
├── Dockerfile                    # Imagen Docker
├── database.ini                  # Config DB (NO en git)
├── tmp.database.ini              # Template de config DB
└── venv/                         # Entorno virtual Python
```

## Comandos de Ejecucion

### Instalacion
```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar en modo desarrollo
pip install -e .

# O instalar con dependencias de desarrollo
pip install -e ".[dev]"  # incluye pytest, black, etc.

# Configurar base de datos
cp tmp.database.ini database.ini
nano database.ini  # editar con credenciales reales
```

### Ejecutar via CLI
```bash
# Activar entorno
source venv/bin/activate

# Ver ayuda
python -m clockcontrol --help

# Modo individual (un reloj)
python -m clockcontrol single --address 192.168.1.201 --port 4370 --password 0

# Modo masivo (todos los relojes activos)
python -m clockcontrol all
```

### Ejecutar via Scripts Bash
```bash
# Modo individual
./scripts/run_single.sh 192.168.1.201 4370 0

# Modo masivo
./scripts/run_all.sh
```

### Tests
```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=clockcontrol

# Solo un archivo
pytest tests/test_attendance.py -v
```

### Linting y Formateo
```bash
# Formatear codigo
black clockcontrol/
isort clockcontrol/

# Verificar estilo
flake8 clockcontrol/

# Verificar tipos
mypy clockcontrol/
```

### Docker
```bash
# Construir imagen
docker build -t clockcontrol .

# Ejecutar modo individual
docker run -e CLOCK_IP=192.168.1.201 clockcontrol

# Ejecutar modo masivo
docker run -e RUN_MODE=all clockcontrol
```

## Guia de Estilo de Codigo

### Imports (orden PEP 8)
```python
# 1. Standard library
import json
import logging
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from typing import List, Optional

# 2. Third-party
import psycopg2
from zk import ZK

# 3. Local
from clockcontrol.core.exceptions import DeviceConnectionError
from clockcontrol.database.connection import DatabaseConnection
```

### Formateo
- Indentacion: 4 espacios (NO tabs)
- Longitud maxima de linea: 100 caracteres
- Encoding: UTF-8
- Usar Black para formateo automatico

### Tipos y Naming
```python
# Variables: snake_case
ip_address = "192.168.1.1"
marks_processed = []

# Constantes: UPPER_SNAKE_CASE
DEFAULT_PORT = 4370
DEFAULT_TIMEOUT = 10

# Clases: PascalCase
class AttendanceProcessor:
    pass

# Dataclasses para modelos
@dataclass
class AttendanceMark:
    carnet: str
    date_mark: str
```

### Manejo de Errores
```python
# Usar excepciones personalizadas
from clockcontrol.core.exceptions import DeviceConnectionError, DatabaseError

try:
    with device.connect() as conn:
        attendances = device.get_attendance(conn)
except DeviceConnectionError as e:
    logger.error(f"Error de conexion: {e}")
    raise
except Exception as e:
    logger.exception("Error inesperado")
    raise
```

### Base de Datos (patron Repository)
```python
# Usar context managers
with self.db.get_cursor() as cur:
    cur.execute(query, (param1, param2))

# Parametros siempre con placeholders
query = "SELECT * FROM tabla WHERE id = %s"
cur.execute(query, (user_id,))  # NUNCA f-strings
```

## API Principal

### Uso Programatico
```python
from clockcontrol import ClockControlApp, Settings

# Crear aplicacion
app = ClockControlApp()
app.initialize()

# Procesar un reloj
result = app.process_single_clock(
    ip="192.168.1.201",
    port=4370,
    password=0
)
print(f"Marcajes: {result.marks_processed}")

# Procesar todos
results = app.process_all_clocks()
```

### Clases Principales
- `ClockControlApp` - Orquestador principal
- `AttendanceProcessor` - Procesa y filtra marcajes
- `ZKDeviceManager` - Conexion a relojes ZKTeco
- `DatabaseConnection` - Pool de conexiones DB
- `ClockRepository` - CRUD de relojes
- `AttendanceRepository` - CRUD de marcajes

## Esquema de Base de Datos

### Tablas Principales
```sql
-- Marcajes de asistencia
rrhh.person_marks (
    id SERIAL PRIMARY KEY,
    carnet VARCHAR(255),
    date_mark VARCHAR(255),
    time_mark VARCHAR(255),
    ip_clock VARCHAR(255),
    id_reloj_bio INT
)

-- Log de conexiones a relojes
rrhh.clock_conn (
    id SERIAL PRIMARY KEY,
    ip_clock VARCHAR(255),
    available BOOLEAN NOT NULL,
    date TIMESTAMP NOT NULL DEFAULT NOW(),
    obs VARCHAR(255)
)

-- Registro de relojes biometricos (tabla externa)
rrhh.reloj_biometrico
```

## Variables de Entorno / Configuracion

El proyecto usa `database.ini` (NO commitear):
```ini
[postgresql]
host=192.168.1.100
database=rrhh_db
user=usuario
password=contrasenya
port=5432
```

## Dependencias

Solo 3 dependencias de produccion:
```
psycopg2-binary>=2.8
pyzk>=0.9
python-dateutil>=2.8
```

Dependencias de desarrollo en pyproject.toml:
- pytest, pytest-cov
- black, isort, flake8
- mypy

## Notas para Agentes

1. **NO modificar** archivos en `venv/`
2. **NO commitear** `database.ini` - contiene credenciales
3. Usar `python -m clockcontrol` para ejecutar, no scripts .py directamente
4. Los tests usan pytest, ejecutar con `pytest -v`
5. Formatear con `black` antes de commitear
6. La configuracion esta centralizada en `clockcontrol/config/settings.py`
7. Todas las excepciones heredan de `ClockControlError`
