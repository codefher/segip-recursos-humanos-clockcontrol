# Guia de Despliegue en Produccion - clockControl v2.0

> Sistema de Control de Asistencia para SEGIP (Bolivia)
> Fecha: Febrero 2026

---

## Tabla de Contenidos

1. [Que es clockControl y como funciona?](#1-que-es-clockcontrol-y-como-funciona)
2. [Conceptos clave que debes entender](#2-conceptos-clave-que-debes-entender)
3. [Requisitos del servidor de produccion](#3-requisitos-del-servidor-de-produccion)
4. [Instalacion paso a paso](#4-instalacion-paso-a-paso)
5. [Configuracion de la base de datos](#5-configuracion-de-la-base-de-datos)
6. [Registro de relojes biometricos en la BD](#6-registro-de-relojes-biometricos-en-la-bd)
7. [Registro de huellas en el reloj ZKTeco](#7-registro-de-huellas-en-el-reloj-zkteco)
8. [Pruebas manuales](#8-pruebas-manuales)
9. [Configuracion del Cron (ejecucion automatica)](#9-configuracion-del-cron-ejecucion-automatica)
10. [Monitoreo y logs](#10-monitoreo-y-logs)
11. [Solucion de problemas comunes](#11-solucion-de-problemas-comunes)
12. [Arquitectura del proyecto](#12-arquitectura-del-proyecto)
13. [Bug conocido corregido](#13-bug-conocido-corregido)

---

## 1. Que es clockControl y como funciona?

**clockControl** es un programa en Python que se conecta a relojes biometricos ZKTeco (de huella dactilar) para extraer los registros de asistencia de los empleados y guardarlos en una base de datos PostgreSQL.

### Flujo completo del sistema:

```
[Empleado pone su huella]
         |
         v
[Reloj ZKTeco guarda el marcaje en su memoria interna]
         |
         v
[clockControl se conecta al reloj cada 5 minutos via red]
         |
         v
[Extrae los marcajes y filtra solo los de hoy y ayer]
         |
         v
[Guarda los nuevos marcajes en PostgreSQL (tabla rrhh.person_marks)]
```

### Que problema resuelve?

Los relojes biometricos guardan los marcajes en su propia memoria, pero esa informacion necesita estar en una base de datos central para:
- Generar reportes de asistencia
- Calcular horas trabajadas
- Controlar puntualidad
- Integrarse con el sistema de recursos humanos

### Como se comunica con los relojes?

- Los relojes ZKTeco se comunican por **red (TCP/UDP)** en el **puerto 4370**
- clockControl usa la libreria **pyzk** para hablar el protocolo nativo de ZKTeco
- Primero hace un **ping** para verificar que el reloj este encendido y accesible
- Luego se conecta y descarga todos los marcajes almacenados

---

## 2. Conceptos clave que debes entender

### Entorno Virtual (venv)

Un **entorno virtual** es una carpeta aislada que contiene su propia version de Python y sus librerias. Esto evita conflictos entre proyectos.

```bash
# Crear un entorno virtual
python3 -m venv venv

# Activarlo (SIEMPRE antes de usar el proyecto)
source venv/bin/activate

# Cuando esta activo, veras (venv) al inicio del prompt:
# (venv) usuario@servidor:~$

# Para desactivarlo
deactivate
```

**Importante:** Siempre debes activar el entorno virtual antes de ejecutar clockControl.

### Cron

**Cron** es el programador de tareas de Linux. Permite ejecutar comandos automaticamente en horarios definidos.

```
*/5 * * * *     = Cada 5 minutos
 |  | | | |
 |  | | | +--- Dia de la semana (0-7, domingo=0 o 7)
 |  | | +----- Mes (1-12)
 |  | +------- Dia del mes (1-31)
 |  +--------- Hora (0-23)
 +------------ Minuto (0-59)
```

Ejemplos:
- `*/5 * * * *` = Cada 5 minutos, todos los dias
- `0 8 * * 1-5` = A las 8:00 AM, de lunes a viernes
- `*/1 * * * *` = Cada minuto

### Puerto 4370

Es el **puerto de red** por defecto que usan los relojes ZKTeco para comunicarse. Es como un "canal" especifico por donde se envian y reciben datos. Si el firewall bloquea este puerto, clockControl no podra conectarse al reloj.

### Stored Procedure (Procedimiento Almacenado)

Es una **funcion que vive dentro de la base de datos** PostgreSQL. En nuestro caso, `rrhh.set_attendance_info_clock()` recibe los marcajes en formato JSON y los inserta en la tabla, **evitando duplicados automaticamente**.

### Ping

Es un comando que envia un paquete de red a un dispositivo para verificar si esta **encendido y accesible**. clockControl hace ping antes de intentar conectarse al reloj.

### psycopg2

Es la libreria de Python que permite conectarse y ejecutar consultas en **PostgreSQL**. Es el "puente" entre Python y la base de datos.

### pyzk

Es la libreria de Python que implementa el **protocolo de comunicacion de ZKTeco**. Permite conectarse a los relojes, descargar marcajes, obtener usuarios, etc.

---

## 3. Requisitos del servidor de produccion

### Sistema Operativo
- **Debian 12 (Bookworm)** o superior (probado en Debian 13 Trixie)
- Cualquier distribucion basada en Debian (Ubuntu, etc.) tambien funciona

### Software necesario
- **Python 3.9** o superior
- **pip** (gestor de paquetes de Python)
- **python3-venv** (para entornos virtuales)
- **git** (para clonar el repositorio)
- **iputils-ping** (para hacer ping a los relojes)

### Red
- El servidor debe tener **acceso de red** a los relojes biometricos (puerto 4370)
- El servidor debe tener **acceso de red** al servidor PostgreSQL (puerto 5432)
- El firewall debe permitir las conexiones salientes a estos puertos

### Base de datos
- **PostgreSQL 12** o superior
- El esquema `rrhh` debe existir
- Las tablas `rrhh.person_marks`, `rrhh.clock_conn` y `rrhh.reloj_biometrico` deben existir
- El stored procedure `rrhh.set_attendance_info_clock` debe estar creado
- El usuario de BD debe tener permisos de SELECT, INSERT y EXECUTE

---

## 4. Instalacion paso a paso

### Paso 1: Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### Paso 2: Instalar dependencias del sistema

```bash
sudo apt install -y python3 python3-pip python3-venv git iputils-ping
```

Verificar que todo esta instalado:

```bash
python3 --version    # Debe mostrar 3.9 o superior
git --version        # Debe mostrar la version de git
ping -c 1 127.0.0.1  # Debe responder
```

### Paso 3: Clonar el repositorio

```bash
# Ir al directorio donde quieras instalar el proyecto
cd /home/admsegip/project/rrhh-new

# Clonar el repositorio (ajusta la URL segun tu servidor Git)
git clone git@gitlab.segip.gob.bo:carlos.pacha/segip-recursos-humanos-clockcontrol.git

# Entrar al directorio del proyecto
cd segip-recursos-humanos-clockcontrol
```

### Paso 4: Ejecutar el script de instalacion

El proyecto incluye un script que automatiza la instalacion:

```bash
bash install.sh
```

Este script hace lo siguiente:
1. Verifica que Python 3 este instalado
2. Crea el entorno virtual (`venv/`)
3. Instala las dependencias (`psycopg2-binary`, `pyzk`, `python-dateutil`)
4. Crea el archivo `database.ini` desde la plantilla
5. Da permisos de ejecucion a los scripts

### Paso 5: Instalacion manual (alternativa si el script falla)

Si prefieres hacerlo manualmente:

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Verificar que las librerias se instalaron
python -c "import psycopg2; print('psycopg2 OK')"
python -c "from zk import ZK; print('pyzk OK')"

# Dar permisos a los scripts
chmod +x scripts/*.sh
```

---

## 5. Configuracion de la base de datos

### Paso 1: Crear el archivo de credenciales

```bash
# Copiar la plantilla
cp tmp.database.ini database.ini

# Editar con las credenciales reales
nano database.ini
```

### Paso 2: Configurar las credenciales

Edita `database.ini` con los datos del servidor PostgreSQL de produccion:

```ini
[postgresql]
host=10.0.5.45
database=ruid
user=usr_recursos_humanos
password=TU_PASSWORD_AQUI
port=5432
```

Campos:
- **host**: IP o hostname del servidor PostgreSQL
- **database**: Nombre de la base de datos
- **user**: Usuario de PostgreSQL
- **password**: Contrasena del usuario
- **port**: Puerto de PostgreSQL (casi siempre 5432)

### Paso 3: Proteger el archivo de credenciales

```bash
# Solo el dueno puede leer/escribir
chmod 600 database.ini
```

**IMPORTANTE:** Este archivo contiene credenciales sensibles. NUNCA lo subas a git (ya esta en `.gitignore`).

### Paso 4: Verificar la conexion

```bash
source venv/bin/activate
python -c "
from clockcontrol.config.settings import get_settings
from clockcontrol.database.connection import DatabaseConnection
settings = get_settings()
db = DatabaseConnection(settings.database.to_dict())
db.ensure_tables_exist()
print('Conexion exitosa!')
"
```

Si ves `Conexion exitosa!` y `Tablas verificadas correctamente`, todo esta bien.

### Paso 5: Verificar que el stored procedure exista

```bash
source venv/bin/activate
python -c "
from clockcontrol.config.settings import get_settings
from clockcontrol.database.connection import DatabaseConnection
settings = get_settings()
db = DatabaseConnection(settings.database.to_dict())
with db.get_cursor() as cur:
    cur.execute(\"SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'rrhh' AND routine_name = 'set_attendance_info_clock'\")
    result = cur.fetchone()
    if result:
        print('Stored procedure encontrado: OK')
    else:
        print('ERROR: Stored procedure NO encontrado. Ejecutar el SQL de creacion.')
"
```

Si el stored procedure no existe, debes crearlo ejecutando:

```bash
psql -h 10.0.5.45 -U usr_recursos_humanos -d ruid -f sql/stored_procedures/001_create_stored_procedure.sql
```

---

## 6. Registro de relojes biometricos en la BD

Para que clockControl pueda procesar un reloj, este debe estar registrado en la tabla `rrhh.reloj_biometrico` con `activo = 1`.

### Verificar relojes registrados

```bash
source venv/bin/activate
python -c "
from clockcontrol.config.settings import get_settings
from clockcontrol.database.connection import DatabaseConnection
settings = get_settings()
db = DatabaseConnection(settings.database.to_dict())
with db.get_cursor() as cur:
    cur.execute('SELECT id_reloj_bio, ip_reloj, descripcion, puerto, clave, activo FROM rrhh.reloj_biometrico WHERE activo = 1')
    rows = cur.fetchall()
    print(f'Relojes activos: {len(rows)}')
    for r in rows:
        print(f'  ID: {r[0]}, IP: {r[1]}, Desc: {r[2]}, Puerto: {r[3]}, Clave: {r[4]}')
    if not rows:
        print('  No hay relojes activos. Debes registrarlos en la base de datos.')
"
```

### Columnas importantes de rrhh.reloj_biometrico

| Columna | Descripcion | Ejemplo |
|---------|-------------|---------|
| id_reloj_bio | ID unico del reloj | 89 |
| ip_reloj | Direccion IP del reloj en la red | 172.16.21.150 |
| descripcion | Nombre descriptivo | RELOJ OFICINA CENTRAL |
| puerto | Puerto de comunicacion | 4370 |
| clave | Contrasena del reloj | 0 |
| activo | 1=activo, 0=inactivo | 1 |

---

## 7. Registro de huellas en el reloj ZKTeco

El registro de huellas se hace **directamente en el dispositivo fisico**, NO desde clockControl.

### Pasos en el reloj:

1. **Presiona el boton Menu/M** en el reloj
2. **Navega a "Gestio de Usuarios"** > **"Nuevo Usuario"**
3. **Configura los campos:**

| Campo | Que poner | Ejemplo |
|-------|-----------|---------|
| **ID de Usuario** | Numero de carnet del funcionario. **ESTE ES EL CAMPO MAS IMPORTANTE** porque es lo que clockControl extrae como identificador | 100400327 |
| **Nombre** | Nombre del funcionario (opcional, solo referencia) | JUAN PEREZ |
| **Privilegios** | Dejalo en "Usuario Normal" | Usuario Normal |
| **Huella** | Selecciona y registra el dedo 3 veces | - |
| **Rostro** | No necesario | 0 |
| **Numero de Tarjeta** | No necesario | - |
| **Contrasena** | No necesario | - |

4. **Registrar la huella:** Selecciona "Huella", el reloj pedira que pongas el **mismo dedo 3 veces**
5. **Guardar** y salir del menu

### Por que es importante el "ID de Usuario"?

Cuando el empleado marca su huella, el reloj genera un registro asi:

```
Attendance 100400327 : 2026-02-13 08:00:00 0
           ^^^^^^^^^
           Este es el "ID de Usuario" que pusiste
```

clockControl toma ese numero como el **carnet** y lo guarda en la base de datos. Si pones un ID incorrecto, no se podra vincular el marcaje con el empleado.

### Configurar la fecha/hora del reloj

**MUY IMPORTANTE:** El reloj debe tener la **fecha y hora correctas**. Si no, los marcajes saldran con fechas equivocadas y clockControl los descartara (solo acepta marcajes de hoy y ayer).

Para configurar:
1. Menu > Sistema > Fecha/Hora
2. Ajustar al dia y hora actual
3. Guardar

---

## 8. Pruebas manuales

### Prueba 1: Verificar conectividad al reloj

```bash
ping -c 2 172.16.21.150
```

Si responde, el reloj es accesible por red.

### Prueba 2: Ejecutar modo individual (un reloj)

```bash
source venv/bin/activate
python -m clockcontrol single --address 172.16.21.150 --port 4370 --password 0
```

Parametros:
- `--address` o `-a`: IP del reloj (obligatorio)
- `--port` o `-p`: Puerto (default: 4370)
- `--password` o `-P`: Contrasena del reloj (default: 0)

Salida esperada:

```
============================================================
  clockControl - Sistema de Control de Asistencia SEGIP
============================================================

  Modo: Individual
  Reloj: 172.16.21.150:4370

  [OK] 172.16.21.150
      Marcajes procesados: 3
      Marcajes guardados:  1
      Tiempo: 1.26s
```

### Prueba 3: Ejecutar modo masivo (todos los relojes)

```bash
source venv/bin/activate
python -m clockcontrol all
```

Este modo consulta la tabla `rrhh.reloj_biometrico`, obtiene todos los relojes con `activo = 1` y los procesa uno por uno.

### Prueba 4: Verificar que el marcaje se guardo en la BD

```bash
source venv/bin/activate
python -c "
from clockcontrol.config.settings import get_settings
from clockcontrol.database.connection import DatabaseConnection
settings = get_settings()
db = DatabaseConnection(settings.database.to_dict())
with db.get_cursor() as cur:
    cur.execute(\"SELECT id, carnet, date_mark, time_mark, ip_clock FROM rrhh.person_marks ORDER BY id DESC LIMIT 5\")
    for r in cur.fetchall():
        print(f'ID: {r[0]} | Carnet: {r[1]} | Fecha: {r[2]} | Hora: {r[3]} | IP: {r[4]}')
"
```

### Prueba 5: Probar los scripts bash

```bash
# Modo individual
./scripts/run_single.sh 172.16.21.150 4370 0

# Modo masivo
./scripts/run_all.sh
```

---

## 9. Configuracion del Cron (ejecucion automatica)

### Paso 1: Abrir el crontab

```bash
crontab -e
```

Si es la primera vez, te preguntara que editor usar. Elige `nano` (opcion 1).

### Paso 2: Agregar la tarea

Agrega esta linea al final del archivo:

```cron
# clockControl - Extraccion automatica de marcajes biometricos cada 5 minutos
*/5 * * * * /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/scripts/run_all.sh >> /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/clockcontrol.log 2>&1
```

**IMPORTANTE:** Ajusta la ruta `/home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/` a la ruta real donde este instalado el proyecto en el servidor de produccion.

Guarda con `Ctrl+O`, Enter, y sal con `Ctrl+X`.

### Paso 3: Verificar que se guardo

```bash
crontab -l
```

Debe mostrar la linea que agregaste.

### Paso 4: Asegurar permisos del script

```bash
chmod +x /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/scripts/run_all.sh
chmod +x /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/scripts/run_single.sh
```

**NOTA:** Si olvidas este paso, el cron fallara con "Permission denied". Este fue un problema que encontramos durante las pruebas.

### Paso 5: Entender cuando se ejecuta

`*/5 * * * *` significa que se ejecuta en los minutos **:00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55** de cada hora. No espera 5 minutos desde la ultima ejecucion, sino que se ejecuta en esos minutos fijos.

Por ejemplo, si configuras el cron a las 14:03:
- Primera ejecucion: **14:05**
- Segunda ejecucion: **14:10**
- Tercera ejecucion: **14:15**
- ... y asi sucesivamente

---

## 10. Monitoreo y logs

### Ver los logs en tiempo real

```bash
tail -f /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/clockcontrol.log
```

Presiona `Ctrl+C` para dejar de ver.

### Ver las ultimas 50 lineas del log

```bash
tail -50 /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/clockcontrol.log
```

### Que significan los mensajes del log

```
# Mensaje normal: Inicio de ejecucion
INFO - Inicializando clockControl...

# Mensaje normal: Tablas de BD verificadas
INFO - Tablas verificadas correctamente

# Mensaje normal: Reloj encontrado en BD
INFO - Reloj encontrado: 172.16.21.150

# Mensaje normal: Ping exitoso
INFO - Ping a 172.16.21.150: OK

# Mensaje normal: Conexion al reloj exitosa
INFO - Conexion exitosa a 172.16.21.150

# Mensaje normal: Marcajes extraidos
INFO - Marcajes obtenidos de 172.16.21.150: 5

# Mensaje normal: Marcajes filtrados (hoy y ayer)
INFO - Marcajes procesados: 3 de 5

# Mensaje normal: Guardados en BD
INFO - Marcajes guardados: 2 nuevos

# Mensaje de advertencia: No se puede hacer ping
INFO - Ping a 172.16.21.148: FALLIDO

# Mensaje de error: Problema con la BD
ERROR - Error de base de datos: connection refused
```

### Verificar que el cron esta funcionando

```bash
# Buscar ejecuciones recientes de clockcontrol en el log
grep "Ejecutado modo masivo" /home/admsegip/project/rrhh-new/segip-recursos-humanos-clockcontrol/clockcontrol.log | tail -5
```

Deberia mostrar lineas con la fecha/hora de cada ejecucion automatica.

---

## 11. Solucion de problemas comunes

### Error: "Permission denied" en el cron

**Causa:** El script no tiene permisos de ejecucion.

**Solucion:**
```bash
chmod +x scripts/run_all.sh scripts/run_single.sh
```

### Error: "Archivo de configuracion 'database.ini' no encontrado"

**Causa:** No se creo el archivo de credenciales.

**Solucion:**
```bash
cp tmp.database.ini database.ini
nano database.ini   # Editar con credenciales reales
```

### Error: "Sin respuesta a ping"

**Causas posibles:**
1. El reloj esta apagado
2. Problema de red (cable, switch)
3. IP incorrecta
4. Firewall bloqueando ICMP

**Verificar:**
```bash
ping -c 4 172.16.21.150
```

### Error: "No se pudo conectar al reloj"

**Causas posibles:**
1. Puerto incorrecto (el default es 4370)
2. Contrasena incorrecta
3. Otro programa ya esta conectado al reloj (solo permite una conexion a la vez)

### Error: "Reloj no encontrado o inactivo en DB"

**Causa:** La IP del reloj no esta registrada en la tabla `rrhh.reloj_biometrico` o su campo `activo` no es 1.

**Solucion:** Registrar el reloj en la tabla con los datos correctos.

### Marcajes procesados > 0 pero guardados = 0

**Causa:** Los marcajes ya existian en la base de datos (el stored procedure evita duplicados). Esto es **normal** si el sistema ya proceso esos marcajes antes.

### La fecha del reloj esta mal

**Causa:** El reloj tiene la fecha/hora desconfigurada.

**Solucion:** En el reloj, ir a Menu > Sistema > Fecha/Hora y corregirla.

**IMPORTANTE:** Si la fecha del reloj es incorrecta, clockControl descartara los marcajes porque solo acepta los de hoy y ayer. Este fue un problema que encontramos durante las pruebas iniciales.

### Error: "Biblioteca pyzk no instalada"

**Solucion:**
```bash
source venv/bin/activate
pip install pyzk
```

### Error de base de datos: "connection refused"

**Causas posibles:**
1. PostgreSQL no esta corriendo
2. Credenciales incorrectas en `database.ini`
3. Firewall bloquea el puerto 5432
4. El host es incorrecto

**Verificar conexion:**
```bash
psql -h 10.0.5.45 -U usr_recursos_humanos -d ruid -c "SELECT 1"
```

---

## 12. Arquitectura del proyecto

### Estructura de archivos

```
segip-recursos-humanos-clockcontrol/
|
|-- clockcontrol/                # Codigo fuente principal
|   |-- __init__.py             # Version del paquete (v2.0.0)
|   |-- __main__.py             # Permite ejecutar: python -m clockcontrol
|   |-- cli.py                  # Logica principal y comandos CLI
|   |
|   |-- core/                   # Logica de negocio
|   |   |-- attendance.py       # Procesa y filtra marcajes
|   |   |-- device.py           # Conexion con relojes ZKTeco
|   |   |-- exceptions.py       # Errores personalizados
|   |
|   |-- database/               # Acceso a base de datos
|   |   |-- connection.py       # Conexion a PostgreSQL
|   |   |-- models.py           # Modelos de datos (Clock, ConnectionLog)
|   |   |-- repositories.py     # Operaciones de lectura/escritura en BD
|   |
|   |-- config/                 # Configuracion
|       |-- settings.py         # Lee database.ini y gestiona configuracion
|
|-- scripts/                    # Scripts para ejecutar desde bash/cron
|   |-- run_single.sh           # Ejecutar un reloj especifico
|   |-- run_all.sh              # Ejecutar todos los relojes activos
|
|-- sql/                        # Scripts SQL
|   |-- stored_procedures/
|       |-- 001_create_stored_procedure.sql   # Funcion para insertar marcajes
|
|-- tests/                      # Tests automatizados
|   |-- test_attendance.py
|
|-- database.ini                # Credenciales BD (NO subir a git)
|-- tmp.database.ini            # Plantilla de database.ini
|-- requirements.txt            # Dependencias de Python
|-- pyproject.toml              # Configuracion del proyecto
|-- install.sh                  # Script de instalacion
|-- clockcontrol.log            # Archivo de logs
|-- Dockerfile                  # Para despliegue con Docker (opcional)
```

### Flujo interno del codigo

```
1. cli.py (ClockControlApp)
   |
   |-- Lee configuracion de database.ini
   |       (config/settings.py)
   |
   |-- Conecta a PostgreSQL
   |       (database/connection.py)
   |
   |-- Obtiene lista de relojes activos de la BD
   |       (database/repositories.py -> ClockRepository)
   |
   |-- Para cada reloj:
   |   |
   |   |-- Hace ping al reloj
   |   |       (core/device.py -> ZKDeviceManager.is_reachable)
   |   |
   |   |-- Se conecta al reloj por puerto 4370
   |   |       (core/device.py -> ZKDeviceManager.connect)
   |   |
   |   |-- Descarga los marcajes crudos
   |   |       (core/device.py -> ZKDeviceManager.get_attendance)
   |   |
   |   |-- Filtra solo marcajes de hoy y ayer
   |   |       (core/attendance.py -> AttendanceProcessor.process)
   |   |
   |   |-- Convierte a JSON
   |   |       (core/attendance.py -> AttendanceProcessor.to_json)
   |   |
   |   |-- Guarda en BD via stored procedure
   |           (database/repositories.py -> AttendanceRepository.save_marks)
   |
   |-- Muestra resumen en pantalla
```

### Tablas de la base de datos

#### rrhh.person_marks (donde se guardan los marcajes)

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| id | SERIAL | ID autoincrementable |
| carnet | VARCHAR | Numero de carnet del empleado (= ID de Usuario del reloj) |
| date_mark | VARCHAR | Fecha del marcaje (YYYY-MM-DD) |
| time_mark | VARCHAR | Hora del marcaje (HH:MM:SS) |
| ip_clock | VARCHAR | IP del reloj donde marco |
| id_reloj_bio | INT | ID del reloj en la tabla reloj_biometrico |

#### rrhh.clock_conn (log de conexiones)

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| id | SERIAL | ID autoincrementable |
| ip_clock | VARCHAR | IP del reloj |
| available | BOOLEAN | true=conexion exitosa, false=fallo |
| date | TIMESTAMP | Fecha/hora del intento |
| obs | VARCHAR | Observacion (error o exito) |

#### rrhh.reloj_biometrico (registro de relojes)

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| id_reloj_bio | INT | ID unico del reloj |
| ip_reloj | VARCHAR | IP del reloj |
| descripcion | VARCHAR | Nombre descriptivo |
| puerto | INT | Puerto (default 4370) |
| clave | INT | Contrasena del reloj |
| activo | SMALLINT | 1=activo, 0=inactivo |

---

## 13. Bug conocido corregido

Durante las pruebas encontramos un bug en `clockcontrol/database/repositories.py` en la linea 117.

### El problema

Los parametros del stored procedure se pasaban como un ARRAY en vez de como parametros separados:

```python
# INCORRECTO (genera error: "sintaxis de entrada no valida para tipo integer")
cur.callproc("rrhh.set_attendance_info_clock", ([4570, marks_json],))

# CORRECTO
cur.callproc("rrhh.set_attendance_info_clock", (4570, marks_json))
```

### La solucion

En el archivo `clockcontrol/database/repositories.py`, linea 117, se cambio de:

```python
cur.callproc("rrhh.set_attendance_info_clock", ([4570, marks_json],))
```

A:

```python
cur.callproc("rrhh.set_attendance_info_clock", (4570, marks_json))
```

**Asegurate de que este cambio este aplicado antes de desplegar en produccion.**

---

## Checklist de despliegue rapido

Usa esta lista para verificar que no te falte nada:

- [ ] Sistema operativo Debian 12+ instalado
- [ ] Python 3.9+ instalado (`python3 --version`)
- [ ] Repositorio clonado en el servidor
- [ ] Ejecutar `bash install.sh` o instalacion manual
- [ ] Permisos de ejecucion en scripts (`chmod +x scripts/*.sh`)
- [ ] Archivo `database.ini` creado con credenciales correctas
- [ ] Permisos restrictivos en database.ini (`chmod 600 database.ini`)
- [ ] Stored procedure creado en PostgreSQL
- [ ] Relojes registrados en tabla `rrhh.reloj_biometrico` con `activo = 1`
- [ ] Verificar conectividad a los relojes (`ping <IP_RELOJ>`)
- [ ] Verificar fecha/hora correcta en cada reloj
- [ ] Huellas registradas en los relojes con el carnet correcto como "ID de Usuario"
- [ ] Bug de repositories.py corregido (parametros del stored procedure)
- [ ] Prueba manual exitosa (`python -m clockcontrol all`)
- [ ] Cron configurado (`crontab -e`)
- [ ] Verificar que el cron funciona (esperar 5 minutos y revisar log)

---

*Documento generado para clockControl v2.0 - SEGIP Bolivia - Febrero 2026*
