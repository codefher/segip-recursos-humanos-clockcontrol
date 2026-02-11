# clockControl

Sistema de control de asistencia para SEGIP (Bolivia) que extrae marcajes de relojes biometricos ZKTeco y los almacena en PostgreSQL.

## Caracteristicas

- Conexion a relojes biometricos ZKTeco via protocolo UDP/TCP
- Extraccion automatica de marcajes de asistencia
- Almacenamiento en PostgreSQL (esquema `rrhh`)
- Ejecucion programada via cron (cada 5 minutos)
- Modo individual (un reloj) y masivo (todos los relojes activos)

## Requisitos

- Linux Debian 12+ (o compatible)
- Python 3.9+
- PostgreSQL 12+
- Acceso de red a relojes ZKTeco

## Instalacion

### 1. Clonar repositorio

```bash
git clone git@gitlab.segip.gob.bo:carlos.pacha/clockcontrol.git
cd clockcontrol
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 3. Configurar base de datos

```bash
cp tmp.database.ini database.ini
nano database.ini
```

Editar con credenciales reales:

```ini
[postgresql]
host=192.168.1.100
database=rrhh_db
user=usuario
password=contrasenya
port=5432
```

## Uso

### Activar entorno virtual

```bash
source venv/bin/activate
```

### Modo individual (un reloj)

```bash
# Via CLI
python -m clockcontrol single --address 192.168.1.201 --port 4370 --password 0

# Via script bash
./scripts/run_single.sh 192.168.1.201 4370 0
```

### Modo masivo (todos los relojes)

```bash
# Via CLI
python -m clockcontrol all

# Via script bash
./scripts/run_all.sh
```

### Ver ayuda

```bash
python -m clockcontrol --help
python -m clockcontrol single --help
python -m clockcontrol all --help
```

## Configuracion de Cron

Para ejecutar automaticamente cada 5 minutos:

```bash
sudo crontab -e
```

Agregar:

```cron
*/5 * * * * /ruta/a/clockcontrol/scripts/run_all.sh >> /var/log/clockcontrol.log 2>&1
```

## Estructura del Proyecto

```
clockcontrol/
├── clockcontrol/              # Paquete principal
│   ├── __init__.py           # API publica
│   ├── __main__.py           # Entry point (python -m)
│   ├── cli.py                # Interface de linea de comandos
│   ├── core/                 # Logica de negocio
│   │   ├── attendance.py     # Procesamiento de marcajes
│   │   ├── device.py         # Conexion a relojes ZK
│   │   └── exceptions.py     # Excepciones personalizadas
│   ├── database/             # Capa de datos
│   │   ├── connection.py     # Gestor de conexiones DB
│   │   ├── models.py         # Modelos de datos
│   │   └── repositories.py   # Repositorios
│   └── config/               # Configuracion
│       └── settings.py       # Configuracion centralizada
├── scripts/                   # Scripts bash
│   ├── run_single.sh         # Ejecutar modo individual
│   └── run_all.sh            # Ejecutar modo masivo
├── tests/                     # Tests unitarios
├── pyproject.toml            # Configuracion del proyecto
├── requirements.txt          # Dependencias
├── database.ini              # Config DB (NO commitear)
└── tmp.database.ini          # Template de config DB
```

## Base de Datos

### Tablas principales

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

-- Log de conexiones
rrhh.clock_conn (
    id SERIAL PRIMARY KEY,
    ip_clock VARCHAR(255),
    available BOOLEAN,
    date TIMESTAMP,
    obs VARCHAR(255)
)

-- Registro de relojes (externa)
rrhh.reloj_biometrico
```

## Desarrollo

### Instalar dependencias de desarrollo

```bash
pip install -e ".[dev]"
```

### Ejecutar tests

```bash
pytest
```

### Formatear codigo

```bash
black clockcontrol/
isort clockcontrol/
```

### Verificar tipos

```bash
mypy clockcontrol/
```

## Autores

- Carlos Pacha Cordova
- Enrique Torrez Amaru
- Equipo SEGIP

## Licencia

Proyecto interno SEGIP - Todos los derechos reservados.
# segip-recursos-humanos-clockcontrol
