# Guia de Implementacion con Docker - clockControl v2.0

> Sistema de Control de Asistencia para SEGIP (Bolivia)
> Fecha: Febrero 2026

---

## Tabla de Contenidos

1. [Que es Docker y por que usarlo?](#1-que-es-docker-y-por-que-usarlo)
2. [Requisitos previos](#2-requisitos-previos)
3. [Estructura de archivos Docker](#3-estructura-de-archivos-docker)
4. [Configuracion antes de ejecutar](#4-configuracion-antes-de-ejecutar)
5. [Levantar el contenedor](#5-levantar-el-contenedor)
6. [Comandos utiles del dia a dia](#6-comandos-utiles-del-dia-a-dia)
7. [Variables de entorno disponibles](#7-variables-de-entorno-disponibles)
8. [Modos de ejecucion](#8-modos-de-ejecucion)
9. [Monitoreo y logs](#9-monitoreo-y-logs)
10. [Detener, reiniciar y actualizar](#10-detener-reiniciar-y-actualizar)
11. [Solucion de problemas](#11-solucion-de-problemas)
12. [Como funciona internamente](#12-como-funciona-internamente)

---

## 1. Que es Docker y por que usarlo?

**Docker** es una herramienta que empaqueta una aplicacion con TODO lo que necesita (Python, librerias, configuracion) en un "contenedor" aislado. Es como una caja que contiene el programa listo para funcionar.

### Ventajas de usar Docker para clockControl:

| Sin Docker | Con Docker |
|---|---|
| Instalar Python manualmente | Ya viene incluido |
| Crear entorno virtual | No es necesario |
| Instalar librerias con pip | Ya vienen instaladas |
| Configurar cron manualmente | El contenedor lo configura solo |
| Dar permisos a scripts | Ya estan configurados |
| Si cambias de servidor, repetir todo | Solo copias y ejecutas `docker compose up` |

### Analogia simple:

- **Sin Docker:** Es como cocinar desde cero: compras ingredientes, preparas, cocinas.
- **Con Docker:** Es como pedir comida lista: solo la calientas y sirves.

---

## 2. Requisitos previos

### En el servidor de produccion necesitas:

1. **Docker Engine** instalado

```bash
# Verificar si Docker esta instalado
docker --version
# Debe mostrar algo como: Docker version 27.x.x

# Verificar que el servicio este corriendo
sudo systemctl status docker
```

2. **Docker Compose** (viene incluido con Docker moderno)

```bash
# Verificar docker compose
docker compose version
# Debe mostrar algo como: Docker Compose version v2.x.x
```

3. **Acceso de red** desde el servidor a:
   - Los relojes biometricos (puerto 4370)
   - El servidor PostgreSQL (puerto 5432)

### Si Docker NO esta instalado:

```bash
# En Debian/Ubuntu
sudo apt update
sudo apt install -y docker.io docker-compose-v2

# Agregar tu usuario al grupo docker (para no usar sudo)
sudo usermod -aG docker $USER

# Cerrar sesion y volver a entrar para que tome efecto
logout
```

---

## 3. Estructura de archivos Docker

```
segip-recursos-humanos-clockcontrol/
|
|-- Dockerfile              # Receta para construir la imagen
|-- docker-compose.yml      # Configuracion para levantar el contenedor
|-- docker-entrypoint.sh    # Script que arranca dentro del contenedor
|-- database.ini            # Credenciales de la BD (debes crearlo)
|-- tmp.database.ini        # Plantilla de database.ini
|-- ...                     # Resto del codigo fuente
```

### Que hace cada archivo:

- **Dockerfile**: Define como se construye la imagen (instala Python, librerias, copia el codigo)
- **docker-compose.yml**: Define como se ejecuta el contenedor (variables, volumenes, red)
- **docker-entrypoint.sh**: Se ejecuta al arrancar el contenedor (configura el cron y mantiene el contenedor vivo)
- **database.ini**: Credenciales de PostgreSQL (lo creas tu, NO se sube a git)

---

## 4. Configuracion antes de ejecutar

### Paso 1: Clonar el repositorio en el servidor

```bash
cd /home/admsegip/project/rrhh-new
git clone git@gitlab.segip.gob.bo:carlos.pacha/segip-recursos-humanos-clockcontrol.git
cd segip-recursos-humanos-clockcontrol
```

### Paso 2: Crear el archivo de credenciales

```bash
cp tmp.database.ini database.ini
nano database.ini
```

Edita con las credenciales reales de produccion:

```ini
[postgresql]
host=10.0.5.45
database=ruid
user=usr_recursos_humanos
password=TU_PASSWORD_AQUI
port=5432
```

Protege el archivo:

```bash
chmod 600 database.ini
```

### Paso 3: Configurar docker-compose.yml (opcional)

El archivo `docker-compose.yml` tiene valores por defecto que funcionan bien. Solo necesitas cambiarlo si quieres:

- Cambiar el intervalo del cron (default: 5 minutos)
- Usar modo individual en vez de masivo
- Especificar un reloj concreto

```yaml
services:
  clockcontrol:
    build: .
    container_name: clockcontrol
    restart: unless-stopped

    volumes:
      - ./database.ini:/app/database.ini:ro    # Monta credenciales (solo lectura)
      - clockcontrol-logs:/app/logs            # Persiste los logs

    environment:
      - RUN_MODE=all           # "all" o "single"
      - CRON_INTERVAL=5        # Cada cuantos minutos se ejecuta

      # Solo si usas RUN_MODE=single:
      # - CLOCK_IP=172.16.21.150
      # - CLOCK_PORT=4370
      # - CLOCK_PASSWORD=0

    network_mode: host         # Acceso directo a la red del servidor

volumes:
  clockcontrol-logs:           # Volumen para guardar los logs
```

---

## 5. Levantar el contenedor

### Construir la imagen y levantar (primera vez):

```bash
docker compose up -d --build
```

Explicacion:
- `docker compose up` = Levantar el contenedor
- `-d` = En segundo plano (detached), no ocupa la terminal
- `--build` = Construir/reconstruir la imagen antes de levantar

### Solo levantar (si la imagen ya esta construida):

```bash
docker compose up -d
```

### Verificar que esta corriendo:

```bash
docker ps
```

Deberias ver algo como:

```
NAMES          STATUS                    PORTS
clockcontrol   Up 5 minutes (healthy)
```

El estado `(healthy)` significa que el contenedor esta funcionando correctamente.

---

## 6. Comandos utiles del dia a dia

### Ver si el contenedor esta corriendo

```bash
docker ps
```

### Ver los logs en tiempo real

```bash
docker logs -f clockcontrol
```

Presiona `Ctrl+C` para salir (el contenedor sigue corriendo).

### Ver las ultimas 50 lineas del log

```bash
docker logs --tail 50 clockcontrol
```

### Ejecutar clockControl manualmente dentro del contenedor

```bash
# Modo masivo (todos los relojes)
docker exec clockcontrol python -m clockcontrol all

# Modo individual (un reloj)
docker exec clockcontrol python -m clockcontrol single --address 172.16.21.150
```

### Entrar al contenedor (terminal interactiva)

```bash
docker exec -it clockcontrol bash
```

Para salir: escribe `exit`

### Hacer ping a un reloj desde el contenedor

```bash
docker exec clockcontrol ping -c 2 172.16.21.150
```

---

## 7. Variables de entorno disponibles

Se configuran en `docker-compose.yml` bajo la seccion `environment`:

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `RUN_MODE` | `all` | Modo de ejecucion: `all` (todos los relojes activos) o `single` (un reloj especifico) |
| `CRON_INTERVAL` | `5` | Cada cuantos minutos se ejecuta automaticamente |
| `CLOCK_IP` | `10.10.24.48` | IP del reloj (solo si `RUN_MODE=single`) |
| `CLOCK_PORT` | `4370` | Puerto del reloj (solo si `RUN_MODE=single`) |
| `CLOCK_PASSWORD` | `0` | Contrasena del reloj (solo si `RUN_MODE=single`) |

### Ejemplo: Cambiar el intervalo a 3 minutos

En `docker-compose.yml`:

```yaml
    environment:
      - CRON_INTERVAL=3
```

Luego reiniciar:

```bash
docker compose down && docker compose up -d
```

---

## 8. Modos de ejecucion

### Modo masivo (recomendado para produccion)

Procesa **todos los relojes activos** registrados en la tabla `rrhh.reloj_biometrico`.

```yaml
    environment:
      - RUN_MODE=all
      - CRON_INTERVAL=5
```

### Modo individual

Procesa **un solo reloj** especificado por IP.

```yaml
    environment:
      - RUN_MODE=single
      - CLOCK_IP=172.16.21.150
      - CLOCK_PORT=4370
      - CLOCK_PASSWORD=0
      - CRON_INTERVAL=5
```

---

## 9. Monitoreo y logs

### Donde estan los logs?

Los logs se guardan en un **volumen Docker** llamado `clockcontrol-logs`. Esto significa que persisten aunque detengas o elimines el contenedor.

### Ver logs del contenedor

```bash
# Tiempo real
docker logs -f clockcontrol

# Ultimas N lineas
docker logs --tail 100 clockcontrol

# Logs de los ultimos 30 minutos
docker logs --since 30m clockcontrol
```

### Ver logs internos del cron

```bash
docker exec clockcontrol cat /app/logs/clockcontrol.log
```

### Verificar el estado del contenedor

```bash
# Ver contenedores corriendo
docker ps

# Ver detalles del contenedor
docker inspect clockcontrol

# Ver uso de recursos (CPU, memoria)
docker stats clockcontrol --no-stream
```

### Que significa cada estado?

| Estado | Significado |
|--------|-------------|
| `Up X minutes (healthy)` | Funcionando correctamente |
| `Up X minutes (unhealthy)` | Hay un problema, revisar logs |
| `Exited (0)` | Se detuvo normalmente |
| `Exited (1)` | Se detuvo por un error |
| `Restarting` | Se esta reiniciando automaticamente |

---

## 10. Detener, reiniciar y actualizar

### Detener el contenedor

```bash
docker compose down
```

Esto detiene y elimina el contenedor, pero **los logs se conservan** en el volumen.

### Reiniciar el contenedor

```bash
docker compose restart
```

### Actualizar despues de cambios en el codigo

Si hiciste cambios en el codigo fuente o en la configuracion:

```bash
# Reconstruir imagen y levantar
docker compose up -d --build
```

### Actualizar solo el database.ini

No necesitas reconstruir. Solo edita `database.ini` y reinicia:

```bash
nano database.ini
docker compose restart
```

### Eliminar todo (contenedor + volumen de logs)

```bash
docker compose down -v
```

**Cuidado:** Esto elimina tambien los logs guardados.

---

## 11. Solucion de problemas

### El contenedor no arranca

```bash
# Ver los logs de error
docker logs clockcontrol

# Si dice "No se encontro /app/database.ini"
# Verificar que database.ini existe en el directorio del proyecto
ls -la database.ini
```

### Error: "Sin respuesta a ping"

El contenedor no puede llegar al reloj por red.

```bash
# Probar ping desde el contenedor
docker exec clockcontrol ping -c 2 172.16.21.150

# Si falla, verificar desde el servidor
ping -c 2 172.16.21.150
```

Posibles causas:
- El reloj esta apagado
- Problema de red
- El contenedor no tiene `network_mode: host` en docker-compose.yml

### Error de base de datos

```bash
# Probar conexion a la BD desde el contenedor
docker exec clockcontrol python -c "
from clockcontrol.config.settings import get_settings
from clockcontrol.database.connection import DatabaseConnection
s = get_settings()
db = DatabaseConnection(s.database.to_dict())
db.ensure_tables_exist()
print('Conexion OK')
"
```

### El contenedor se reinicia constantemente

```bash
# Ver por que se murio
docker logs --tail 20 clockcontrol

# Ver el estado
docker inspect clockcontrol --format '{{.State.Status}} - {{.State.ExitCode}}'
```

### Verificar que el cron interno funciona

```bash
# Ver el crontab dentro del contenedor
docker exec clockcontrol crontab -l

# Debe mostrar:
# */5 * * * * cd /app && /usr/local/bin/python -m clockcontrol all >> /app/logs/clockcontrol.log 2>&1
```

---

## 12. Como funciona internamente

### Que pasa cuando ejecutas `docker compose up -d`?

```
1. Docker lee docker-compose.yml
   |
2. Construye la imagen desde Dockerfile (si es necesario)
   |   - Usa Python 3.11 como base
   |   - Instala cron e iputils-ping
   |   - Instala psycopg2, pyzk, python-dateutil
   |   - Copia el codigo fuente
   |
3. Crea el contenedor con la configuracion:
   |   - Monta database.ini (credenciales BD)
   |   - Monta volumen para logs
   |   - Configura red en modo host
   |
4. Ejecuta docker-entrypoint.sh:
   |   - Verifica que database.ini existe
   |   - Configura el cron con el intervalo definido
   |   - Ejecuta clockControl UNA VEZ de prueba
   |   - Inicia el servicio cron
   |   - Se queda mostrando los logs (tail -f)
   |
5. Cada N minutos (CRON_INTERVAL):
       - El cron ejecuta: python -m clockcontrol all
       - Conecta a cada reloj activo
       - Extrae marcajes
       - Guarda en PostgreSQL
       - Registra en el log
```

### Diagrama del contenedor:

```
+------------------------------------------+
|         Contenedor Docker                |
|                                          |
|   +------------------+                   |
|   |  Cron Service    |                   |
|   |  (cada 5 min)    |                   |
|   +--------+---------+                   |
|            |                             |
|            v                             |
|   +------------------+                   |
|   |  clockControl    |                   |
|   |  Python 3.11     |                   |
|   +--------+---------+                   |
|            |                             |
+------------|-----------------------------+
             |
     network_mode: host
             |
     +-------+--------+
     |                 |
     v                 v
+----------+   +--------------+
| Relojes  |   | PostgreSQL   |
| ZKTeco   |   | 10.0.5.45    |
| :4370    |   | :5432        |
+----------+   +--------------+
```

### Archivo database.ini (montado como volumen):

```
[postgresql]
host=10.0.5.45         <-- IP del servidor PostgreSQL
database=ruid          <-- Nombre de la base de datos
user=usr_recursos_humanos  <-- Usuario
password=xxxxx         <-- Contrasena
port=5432              <-- Puerto
```

Este archivo se monta como **solo lectura** (`:ro`) dentro del contenedor en `/app/database.ini`.

---

## Resumen rapido de comandos

```bash
# === LEVANTAR ===
docker compose up -d --build     # Primera vez (construir + levantar)
docker compose up -d             # Levantar (imagen ya construida)

# === MONITOREAR ===
docker ps                        # Ver si esta corriendo
docker logs -f clockcontrol      # Ver logs en tiempo real
docker logs --tail 50 clockcontrol  # Ultimas 50 lineas

# === EJECUTAR MANUALMENTE ===
docker exec clockcontrol python -m clockcontrol all      # Modo masivo
docker exec clockcontrol python -m clockcontrol single --address 172.16.21.150  # Modo individual

# === DETENER / REINICIAR ===
docker compose restart           # Reiniciar
docker compose down              # Detener y eliminar contenedor
docker compose down -v           # Detener + eliminar logs

# === DEPURAR ===
docker exec -it clockcontrol bash   # Entrar al contenedor
docker exec clockcontrol crontab -l # Ver cron interno
docker exec clockcontrol ping -c 2 172.16.21.150  # Probar red
```

---

*Documento generado para clockControl v2.0 - SEGIP Bolivia - Febrero 2026*
