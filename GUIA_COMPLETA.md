# Guia Completa - clockControl v2.0

> Sistema de Control de Asistencia para SEGIP (Bolivia)

---

## Tabla de Contenidos

1. [Que es clockControl?](#1-que-es-clockcontrol)
2. [Como funciona el sistema?](#2-como-funciona-el-sistema)
3. [Arquitectura del proyecto](#3-arquitectura-del-proyecto)
4. [Instalacion paso a paso en Debian](#4-instalacion-paso-a-paso-en-debian)
5. [Configuracion](#5-configuracion)
6. [Uso del sistema](#6-uso-del-sistema)
7. [Configurar ejecucion automatica (Cron)](#7-configurar-ejecucion-automatica-cron)
8. [Entendiendo el codigo](#8-entendiendo-el-codigo)
9. [Base de datos](#9-base-de-datos)
10. [Solucion de problemas](#10-solucion-de-problemas)
11. [Glosario](#11-glosario)

---

## 1. Que es clockControl?

**clockControl** es un programa que se conecta a relojes biometricos (de huella dactilar) para extraer los registros de entrada y salida de los empleados de SEGIP.

### El problema que resuelve:

Los empleados marcan su asistencia poniendo su huella en relojes biometricos ZKTeco ubicados en diferentes oficinas. Estos relojes guardan los marcajes en su memoria interna, pero esa informacion necesita ser extraida y guardada en una base de datos central para:

- Generar reportes de asistencia
- Calcular horas trabajadas
- Controlar puntualidad
- Integrarse con el sistema de recursos humanos

### Que hace clockControl:

```
[Empleado] --> [Pone huella] --> [Reloj ZKTeco] --> [clockControl extrae] --> [PostgreSQL]
```

1. Se conecta a cada reloj biometrico via red (protocolo UDP/TCP)
2. Extrae los marcajes almacenados
3. Filtra solo los marcajes de hoy y ayer (para no duplicar)
4. Guarda los nuevos marcajes en la base de datos PostgreSQL

---

## 2. Como funciona el sistema?

### Flujo de datos paso a paso:

```
+------------------+     +-------------------+     +------------------+
|   PASO 1         |     |   PASO 2          |     |   PASO 3         |
|   Verificar      | --> |   Conectar al     | --> |   Extraer        |
|   conectividad   |     |   reloj ZKTeco    |     |   marcajes       |
|   (ping)         |     |   (puerto 4370)   |     |                  |
+------------------+     +-------------------+     +------------------+
                                                           |
                                                           v
+------------------+     +-------------------+     +------------------+
|   PASO 6         |     |   PASO 5          |     |   PASO 4         |
|   Guardar en     | <-- |   Convertir a     | <-- |   Filtrar por    |
|   PostgreSQL     |     |   formato JSON    |     |   fecha          |
+------------------+     +-------------------+     +------------------+
```

### Ejemplo real:

1. **8:00 AM** - Juan pone su huella en el reloj de la oficina central
2. El reloj guarda: `Carnet: 12345, Fecha: 2026-02-07, Hora: 08:00:00`
3. **Cada 5 minutos** - clockControl se ejecuta automaticamente
4. Conecta al reloj `192.168.1.201` puerto `4370`
5. Extrae todos los marcajes del reloj
6. Filtra: solo toma marcajes de hoy (07/02) y ayer (06/02)
7. Guarda en PostgreSQL tabla `rrhh.person_marks`

### Formato de marcaje del reloj:

Cuando el reloj envia los datos, vienen en este formato:
```
Attendance 12345 : 2026-02-07 08:00:00 0
          ^^^^^   ^^^^^^^^^^  ^^^^^^^^ ^
          carnet  fecha       hora     status
```

clockControl parsea esto y lo convierte en:
```json
{
  "incarnet": "12345",
  "indate_mark": "2026-02-07",
  "intime_mark": "08:00:00",
  "inip_clock": "192.168.1.201",
  "inid_reloj_bio": 42
}
```

---

## 3. Arquitectura del proyecto

### Estructura de carpetas:

```
clockcontrol/
│
├── clockcontrol/              # <-- Paquete principal de Python
│   ├── __init__.py           # API publica (lo que se puede importar)
│   ├── __main__.py           # Permite ejecutar: python -m clockcontrol
│   ├── cli.py                # Interfaz de linea de comandos
│   │
│   ├── core/                 # <-- Logica de negocio
│   │   ├── attendance.py     # Procesa marcajes (filtrar, convertir)
│   │   ├── device.py         # Conexion con relojes ZKTeco
│   │   └── exceptions.py     # Errores personalizados
│   │
│   ├── database/             # <-- Todo lo relacionado con la BD
│   │   ├── connection.py     # Conexion a PostgreSQL
│   │   ├── models.py         # Modelos de datos (Clock, ConnectionLog)
│   │   └── repositories.py   # Operaciones CRUD
│   │
│   └── config/               # <-- Configuracion
│       └── settings.py       # Lee database.ini
│
├── scripts/                   # Scripts bash para cron
│   ├── run_single.sh         # Ejecutar un reloj
│   └── run_all.sh            # Ejecutar todos los relojes
│
├── tests/                     # Tests automatizados
│   └── test_attendance.py
│
├── sql/                       # Scripts SQL
│   └── stored_procedures/
│
├── pyproject.toml            # Configuracion del proyecto Python
├── requirements.txt          # Dependencias
├── database.ini              # Credenciales BD (NO subir a git!)
└── tmp.database.ini          # Plantilla de database.ini
```

### Diagrama de clases simplificado:

```
ClockControlApp (cli.py)
    |
    |-- Settings (config/settings.py)
    |       Lee database.ini
    |
    |-- DatabaseConnection (database/connection.py)
    |       Conexion a PostgreSQL
    |
    |-- ClockRepository (database/repositories.py)
    |       Obtiene lista de relojes
    |
    |-- AttendanceRepository (database/repositories.py)
    |       Guarda marcajes
    |
    |-- ZKDeviceManager (core/device.py)
    |       Conecta a relojes ZKTeco
    |
    |-- AttendanceProcessor (core/attendance.py)
            Filtra y procesa marcajes
```

---

## 4. Instalacion paso a paso en Debian

### Requisitos previos:

- Debian 12 o superior
- Python 3.9 o superior
- Acceso a red donde estan los relojes
- Credenciales de PostgreSQL

### Paso 1: Actualizar sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### Paso 2: Instalar dependencias del sistema

```bash
sudo apt install -y python3 python3-pip python3-venv git iputils-ping
```

### Paso 3: Clonar el repositorio

```bash
# Ir a tu directorio de proyectos
cd ~

# Clonar (ajusta la URL segun tu repositorio)
git clone git@gitlab.segip.gob.bo:carlos.pacha/clockcontrol.git

# Entrar al directorio
cd clockcontrol
```

### Paso 4: Crear entorno virtual

```bash
# Crear entorno virtual llamado "venv"
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate

# Verificar que estas en el entorno (debe mostrar "venv" al inicio)
# (venv) usuario@servidor:~/clockcontrol$
```

### Paso 5: Instalar el proyecto

```bash
# Instalar clockcontrol en modo desarrollo
pip install -e .

# O si quieres las herramientas de desarrollo (pytest, black, etc)
pip install -e ".[dev]"
```

### Paso 6: Verificar instalacion

```bash
# Debe mostrar la ayuda del CLI
python -m clockcontrol --help
```

Salida esperada:
```
usage: clockcontrol [-h] {single,all} ...

Sistema de Control de Asistencia - SEGIP

positional arguments:
  {single,all}  Comandos disponibles
    single      Obtener marcajes de un solo reloj
    all         Obtener marcajes de todos los relojes activos

optional arguments:
  -h, --help    show this help message and exit
```

---

## 5. Configuracion

### Paso 1: Crear archivo de configuracion

```bash
# Copiar la plantilla
cp tmp.database.ini database.ini

# Editar con nano (o tu editor preferido)
nano database.ini
```

### Paso 2: Configurar credenciales

Edita `database.ini` con los datos reales:

```ini
[postgresql]
host=192.168.1.100
database=rrhh_db
user=tu_usuario
password=tu_contraseña_segura
port=5432
```

**IMPORTANTE:** 
- Este archivo contiene credenciales sensibles
- NUNCA lo subas a git (ya esta en .gitignore)
- Usa permisos restrictivos: `chmod 600 database.ini`

### Paso 3: Verificar conectividad a la base de datos

```bash
# Probar conexion con psql (opcional)
psql -h 192.168.1.100 -U tu_usuario -d rrhh_db -c "SELECT 1"
```

### Paso 4: Verificar conectividad a un reloj

```bash
# Hacer ping a un reloj
ping -c 2 192.168.1.201

# Si responde, el reloj es alcanzable
```

---

## 6. Uso del sistema

### Activar entorno virtual (siempre antes de usar)

```bash
cd ~/clockcontrol
source venv/bin/activate
```

### Modo individual (un solo reloj)

```bash
python -m clockcontrol single --address 192.168.1.201 --port 4370 --password 0
```

Parametros:
- `--address` o `-a`: IP del reloj (obligatorio)
- `--port` o `-p`: Puerto del reloj (default: 4370)
- `--password` o `-P`: Contraseña del reloj (default: 0)

Ejemplo de salida:
```
============================================================
  clockControl - Sistema de Control de Asistencia SEGIP
============================================================

  Modo: Individual
  Reloj: 192.168.1.201:4370

  [✓] 192.168.1.201
      Marcajes procesados: 45
      Marcajes guardados:  12
      Tiempo: 2.34s
```

### Modo masivo (todos los relojes)

```bash
python -m clockcontrol all
```

Este modo:
1. Consulta la tabla `rrhh.reloj_biometrico` 
2. Obtiene todos los relojes con `activo = 1`
3. Procesa cada uno secuencialmente

Ejemplo de salida:
```
============================================================
  clockControl - Sistema de Control de Asistencia SEGIP
============================================================

  Modo: Masivo (todos los relojes)

  [✓] 192.168.1.201
      Marcajes procesados: 45
      Marcajes guardados:  12
      Tiempo: 2.34s

  [✓] 192.168.1.202
      Marcajes procesados: 32
      Marcajes guardados:  8
      Tiempo: 1.87s

  [✗] 192.168.1.203
      Marcajes procesados: 0
      Marcajes guardados:  0
      Tiempo: 10.02s
      Error: Sin respuesta a ping

============================================================
  RESUMEN
============================================================
  Relojes procesados: 2/3
  Marcajes procesados: 77
  Marcajes guardados: 20
  Tiempo total: 14.23s
============================================================
```

### Usando scripts bash

```bash
# Modo individual
./scripts/run_single.sh 192.168.1.201 4370 0

# Modo masivo
./scripts/run_all.sh
```

---

## 7. Configurar ejecucion automatica (Cron)

El sistema debe ejecutarse automaticamente cada 5 minutos para mantener la base de datos actualizada.

### Paso 1: Abrir crontab

```bash
crontab -e
```

### Paso 2: Agregar la tarea

Agrega esta linea al final del archivo:

```cron
*/5 * * * * /home/tu_usuario/clockcontrol/scripts/run_all.sh >> /var/log/clockcontrol.log 2>&1
```

Explicacion:
- `*/5 * * * *` = Cada 5 minutos, todos los dias
- `/home/tu_usuario/clockcontrol/scripts/run_all.sh` = Script a ejecutar
- `>> /var/log/clockcontrol.log` = Guardar salida en log
- `2>&1` = Incluir errores en el log

### Paso 3: Verificar que se guardo

```bash
crontab -l
```

### Paso 4: Crear archivo de log

```bash
sudo touch /var/log/clockcontrol.log
sudo chown tu_usuario:tu_usuario /var/log/clockcontrol.log
```

### Paso 5: Monitorear ejecucion

```bash
# Ver ultimas lineas del log en tiempo real
tail -f /var/log/clockcontrol.log
```

---

## 8. Entendiendo el codigo

### Para principiantes en Python:

#### Dataclasses (modelos de datos)

```python
from dataclasses import dataclass

@dataclass
class AttendanceMark:
    carnet: str
    date_mark: str
    time_mark: str
    ip_clock: str
    id_reloj_bio: int
```

Esto es equivalente a:
```python
class AttendanceMark:
    def __init__(self, carnet, date_mark, time_mark, ip_clock, id_reloj_bio):
        self.carnet = carnet
        self.date_mark = date_mark
        # ... etc
```

`@dataclass` genera automaticamente `__init__`, `__repr__`, etc.

#### Context Managers (with)

```python
# En lugar de:
conn = database.connect()
try:
    # hacer algo
finally:
    conn.close()

# Usamos:
with database.connect() as conn:
    # hacer algo
# Se cierra automaticamente
```

#### Type Hints (anotaciones de tipos)

```python
def process(self, ip: str, port: int = 4370) -> bool:
    #              ^^^^       ^^^^^            ^^^^^^
    #              tipo       tipo con default  tipo retorno
```

No son obligatorios pero ayudan a entender el codigo.

### Archivos clave explicados:

#### `clockcontrol/core/attendance.py`

```python
class AttendanceProcessor:
    """Procesa y filtra marcajes"""
    
    def __init__(self, days_back: int = 1):
        # days_back=1 significa: filtrar hoy y ayer
        self.days_back = days_back
    
    def process(self, raw_attendances, ip_clock, clock_id):
        # 1. Calcula rango de fechas
        today = date.today()
        start_date = today - timedelta(days=self.days_back)
        
        # 2. Filtra marcajes
        for attendance in raw_attendances:
            mark = self._parse_attendance(attendance, ip_clock, clock_id)
            if self._is_in_date_range(mark.date_mark, start_date, today):
                processed.append(mark)
        
        return processed
```

#### `clockcontrol/core/device.py`

```python
class ZKDeviceManager:
    """Conecta con relojes ZKTeco"""
    
    def is_reachable(self):
        # Hace ping al reloj
        command = f"ping -c 2 {self.ip}"
        return os.system(command) == 0
    
    def connect(self):
        # Usa la libreria pyzk para conectar
        conn = self._zk.connect()
        return conn
    
    def get_attendance(self, conn):
        # Obtiene marcajes del reloj
        return conn.get_attendance()
```

#### `clockcontrol/cli.py`

```python
class ClockControlApp:
    """Orquestador principal"""
    
    def process_single_clock(self, ip, port, password):
        # 1. Verificar que el reloj existe en BD
        clock = self.clock_repo.get_by_ip(ip)
        
        # 2. Verificar conectividad
        device = ZKDeviceManager(ip, port, password)
        if not device.is_reachable():
            return error
        
        # 3. Conectar y obtener marcajes
        with device.connect() as conn:
            raw_attendances = device.get_attendance(conn)
        
        # 4. Procesar marcajes
        marks = self.processor.process(raw_attendances, ip, clock.id)
        
        # 5. Guardar en BD
        json_data = AttendanceProcessor.to_json(marks)
        self.attendance_repo.save_marks(json_data)
```

---

## 9. Base de datos

### Tablas utilizadas:

#### `rrhh.person_marks` - Marcajes de asistencia

```sql
CREATE TABLE rrhh.person_marks (
    id SERIAL PRIMARY KEY,
    carnet VARCHAR(255),      -- Numero de carnet del empleado
    date_mark VARCHAR(255),   -- Fecha del marcaje (YYYY-MM-DD)
    time_mark VARCHAR(255),   -- Hora del marcaje (HH:MM:SS)
    ip_clock VARCHAR(255),    -- IP del reloj donde marco
    id_reloj_bio INT          -- ID del reloj en reloj_biometrico
);
```

#### `rrhh.clock_conn` - Log de conexiones

```sql
CREATE TABLE rrhh.clock_conn (
    id SERIAL PRIMARY KEY,
    ip_clock VARCHAR(255),    -- IP del reloj
    available BOOLEAN,        -- true=conectado, false=fallo
    date TIMESTAMP DEFAULT NOW(),
    obs VARCHAR(255)          -- Observacion (error, exito, etc)
);
```

#### `rrhh.reloj_biometrico` - Registro de relojes (externa)

Esta tabla ya existe y contiene:
- ID del reloj
- IP del reloj (columna 4)
- Password (columna 6)
- Puerto (columna 12)
- Estado activo/inactivo

### Stored Procedure:

El sistema usa un stored procedure para insertar marcajes evitando duplicados:

```sql
rrhh.set_attendance_info_clock(id_in INTEGER, obj_marks JSON)
```

---

## 10. Solucion de problemas

### Error: "Archivo de configuracion no encontrado"

```
ConfigurationError: Archivo de configuracion 'database.ini' no encontrado
```

**Solucion:**
```bash
cp tmp.database.ini database.ini
nano database.ini  # Editar con credenciales correctas
```

### Error: "Sin respuesta a ping"

```
Error: Sin respuesta a ping
```

**Posibles causas:**
1. El reloj esta apagado
2. Problema de red (cable, switch)
3. IP incorrecta
4. Firewall bloqueando

**Verificar:**
```bash
ping -c 4 192.168.1.201
```

### Error: "No se pudo conectar al reloj"

```
DeviceConnectionError: No se pudo conectar a 192.168.1.201:4370
```

**Posibles causas:**
1. Puerto incorrecto (default es 4370)
2. Password incorrecto
3. Reloj ocupado (otra conexion activa)
4. Protocolo incorrecto (UDP vs TCP)

### Error: "Biblioteca pyzk no instalada"

```
DeviceConnectionError: Biblioteca pyzk no instalada
```

**Solucion:**
```bash
source venv/bin/activate
pip install pyzk
```

### Error de base de datos

```
DatabaseError: Error de base de datos: connection refused
```

**Verificar:**
1. PostgreSQL esta corriendo?
2. Credenciales correctas en database.ini?
3. Firewall permite conexion al puerto 5432?

```bash
# Probar conexion
psql -h 192.168.1.100 -U usuario -d database
```

### Ver logs detallados

```bash
# El sistema genera logs en clockcontrol.log
tail -100 clockcontrol.log

# O en tiempo real
tail -f clockcontrol.log
```

---

## 11. Glosario

| Termino | Significado |
|---------|-------------|
| **ZKTeco** | Marca de relojes biometricos |
| **Marcaje** | Registro de entrada/salida de un empleado |
| **Carnet** | Numero de identificacion del empleado |
| **pyzk** | Libreria Python para comunicarse con relojes ZKTeco |
| **psycopg2** | Libreria Python para PostgreSQL |
| **Cron** | Programador de tareas de Linux |
| **venv** | Entorno virtual de Python (aislamiento de dependencias) |
| **pip** | Gestor de paquetes de Python |
| **Stored Procedure** | Funcion almacenada en la base de datos |
| **UDP/TCP** | Protocolos de comunicacion de red |
| **Puerto 4370** | Puerto por defecto de relojes ZKTeco |

---

## Contacto y soporte

- **Repositorio:** gitlab.segip.gob.bo/carlos.pacha/clockcontrol
- **Autores originales:** Carlos Pacha, Enrique Torrez
- **Refactorizado:** 2026

---

*Documento generado para clockControl v2.0*
