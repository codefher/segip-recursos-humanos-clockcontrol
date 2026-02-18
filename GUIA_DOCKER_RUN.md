# Guia de Implementacion con Docker Run - clockControl v2.0

> Sistema de Control de Asistencia para SEGIP (Bolivia)
> Fecha: Febrero 2026

---

## Tabla de Contenidos

1. [Requisitos previos](#1-requisitos-previos)
2. [Construir la imagen](#2-construir-la-imagen)
3. [Preparar el archivo database.ini](#3-preparar-el-archivo-databaseini)
4. [Ejecutar el contenedor](#4-ejecutar-el-contenedor)
5. [Variables de entorno](#5-variables-de-entorno)
6. [Ejemplos de ejecucion](#6-ejemplos-de-ejecucion)
7. [Comandos de monitoreo](#7-comandos-de-monitoreo)
8. [Detener y reiniciar](#8-detener-y-reiniciar)
9. [Actualizar la imagen](#9-actualizar-la-imagen)
10. [Solucion de problemas](#10-solucion-de-problemas)

---

## 1. Requisitos previos

- Docker Engine instalado en el servidor
- Acceso de red a los relojes biometricos (puerto 4370)
- Acceso de red al servidor PostgreSQL (puerto 5432)

Verificar Docker:

```bash
docker --version
```

---

## 2. Construir la imagen

Desde el directorio del proyecto:

```bash
docker build -t clockcontrol:2.0 .
```

Verificar que se creo:

```bash
docker images | grep clockcontrol
```

Salida esperada:

```
clockcontrol   2.0   3ab7426c7c7d   2 minutes ago   285MB
```

### Alternativa: Cargar imagen desde archivo tar

Si te entregan la imagen como archivo:

```bash
# Cargar imagen
docker load -i clockcontrol-2.0.tar

# Verificar
docker images | grep clockcontrol
```

### Exportar imagen para entregar

```bash
docker save clockcontrol:2.0 -o clockcontrol-2.0.tar
```

---

## 3. Preparar el archivo database.ini

Este archivo contiene las credenciales de PostgreSQL. Debe existir en el servidor antes de ejecutar el contenedor.

### Crear el archivo

```bash
nano /etc/clockcontrol/database.ini
```

Contenido (ajustar con datos reales de produccion):

```ini
[postgresql]
host=10.0.5.45
database=ruid
user=usr_recursos_humanos
password=TU_PASSWORD_AQUI
port=5432
```

### Proteger el archivo

```bash
chmod 600 /etc/clockcontrol/database.ini
```

**Nota:** Puedes colocar el archivo en cualquier ruta del servidor. En esta guia usamos `/etc/clockcontrol/database.ini` como ejemplo, pero puede ser `/home/usuario/database.ini` o cualquier otra ruta. Lo importante es usar la misma ruta en el comando `docker run`.

---

## 4. Ejecutar el contenedor

### Comando basico (modo masivo, todos los relojes, cada 5 minutos):

```bash
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=all \
  -e CRON_INTERVAL=5 \
  clockcontrol:2.0
```

### Explicacion de cada parametro:

```
docker run -d \
```
> `-d` = Ejecutar en segundo plano (detached). El contenedor corre sin ocupar la terminal.

```
  --name clockcontrol \
```
> `--name` = Nombre del contenedor. Se usa para referenciarlo despues (logs, stop, restart).

```
  --restart unless-stopped \
```
> `--restart` = Si el contenedor se cae o el servidor se reinicia, Docker lo levanta automaticamente. Solo se detiene si tu lo paras manualmente.

```
  --network host \
```
> `--network host` = El contenedor usa la red del servidor directamente. Necesario para que pueda hacer ping y conectarse a los relojes biometricos y a PostgreSQL.

```
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
```
> `-v` = Montar un archivo del servidor dentro del contenedor.
> - `/etc/clockcontrol/database.ini` = Ruta del archivo EN EL SERVIDOR
> - `/app/database.ini` = Ruta donde se monta DENTRO del contenedor (no cambiar)
> - `:ro` = Solo lectura (read-only), el contenedor no puede modificarlo

```
  -e RUN_MODE=all \
```
> `-e` = Variable de entorno. `RUN_MODE=all` significa procesar todos los relojes activos.

```
  -e CRON_INTERVAL=5 \
```
> `-e` = Variable de entorno. `CRON_INTERVAL=5` significa ejecutar cada 5 minutos.

```
  clockcontrol:2.0
```
> Nombre y version de la imagen a usar.

---

## 5. Variables de entorno

Se pasan con `-e` en el comando `docker run`:

| Variable | Obligatorio | Default | Descripcion |
|----------|-------------|---------|-------------|
| `RUN_MODE` | No | `all` | `all` = todos los relojes, `single` = un reloj |
| `CRON_INTERVAL` | No | `5` | Cada cuantos minutos se ejecuta |
| `CLOCK_IP` | Solo si single | `10.10.24.48` | IP del reloj |
| `CLOCK_PORT` | No | `4370` | Puerto del reloj |
| `CLOCK_PASSWORD` | No | `0` | Contrasena del reloj |

### Volumen obligatorio

| Volumen | Descripcion |
|---------|-------------|
| `-v /ruta/database.ini:/app/database.ini:ro` | **Obligatorio.** Credenciales de PostgreSQL |

---

## 6. Ejemplos de ejecucion

### Ejemplo 1: Modo masivo, cada 5 minutos (PRODUCCION)

Procesa todos los relojes activos de la tabla `rrhh.reloj_biometrico`:

```bash
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=all \
  -e CRON_INTERVAL=5 \
  clockcontrol:2.0
```

### Ejemplo 2: Modo masivo, cada 1 minuto

```bash
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=all \
  -e CRON_INTERVAL=1 \
  clockcontrol:2.0
```

### Ejemplo 3: Modo individual, un solo reloj

```bash
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=single \
  -e CLOCK_IP=172.16.21.150 \
  -e CLOCK_PORT=4370 \
  -e CLOCK_PASSWORD=0 \
  -e CRON_INTERVAL=5 \
  clockcontrol:2.0
```

### Ejemplo 4: Ejecucion unica (sin cron, solo una vez)

Si quieres ejecutar una sola vez y que el contenedor se detenga:

```bash
docker run --rm \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  clockcontrol:2.0 \
  python -m clockcontrol all
```

> `--rm` = Eliminar el contenedor al terminar.
> Se reemplaza el entrypoint con el comando directo.

---

## 7. Comandos de monitoreo

### Ver si el contenedor esta corriendo

```bash
docker ps
```

Salida esperada:

```
NAMES          STATUS                    PORTS
clockcontrol   Up 10 minutes (healthy)
```

### Ver logs en tiempo real

```bash
docker logs -f clockcontrol
```

Presionar `Ctrl+C` para salir (el contenedor sigue corriendo).

### Ver ultimas N lineas del log

```bash
docker logs --tail 50 clockcontrol
```

### Ver logs de los ultimos 30 minutos

```bash
docker logs --since 30m clockcontrol
```

### Ejecutar clockControl manualmente dentro del contenedor

```bash
docker exec clockcontrol python -m clockcontrol all
```

### Verificar el cron interno

```bash
docker exec clockcontrol crontab -l
```

### Hacer ping a un reloj desde el contenedor

```bash
docker exec clockcontrol ping -c 2 172.16.21.150
```

### Ver uso de recursos

```bash
docker stats clockcontrol --no-stream
```

---

## 8. Detener y reiniciar

### Detener el contenedor

```bash
docker stop clockcontrol
```

### Iniciar un contenedor detenido

```bash
docker start clockcontrol
```

### Reiniciar el contenedor

```bash
docker restart clockcontrol
```

### Eliminar el contenedor (debe estar detenido)

```bash
docker stop clockcontrol
docker rm clockcontrol
```

### Eliminar en un solo comando

```bash
docker rm -f clockcontrol
```

---

## 9. Actualizar la imagen

Cuando haya una nueva version del codigo:

```bash
# 1. Detener y eliminar el contenedor actual
docker rm -f clockcontrol

# 2. Construir la nueva imagen (desde el directorio del proyecto actualizado)
docker build -t clockcontrol:2.0 .

# 3. Levantar con el mismo comando de siempre
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=all \
  -e CRON_INTERVAL=5 \
  clockcontrol:2.0
```

Si reciben la imagen como archivo tar:

```bash
# 1. Detener y eliminar
docker rm -f clockcontrol

# 2. Cargar nueva imagen
docker load -i clockcontrol-2.0.tar

# 3. Levantar
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=all \
  -e CRON_INTERVAL=5 \
  clockcontrol:2.0
```

---

## 10. Solucion de problemas

### El contenedor no arranca

```bash
docker logs clockcontrol
```

Si dice **"No se encontro /app/database.ini"**:
- Verificar que el archivo existe en la ruta que especificaste con `-v`
- Verificar que la ruta es correcta y absoluta

### Error: "Sin respuesta a ping"

```bash
# Verificar desde el contenedor
docker exec clockcontrol ping -c 2 <IP_DEL_RELOJ>

# Verificar desde el servidor
ping -c 2 <IP_DEL_RELOJ>
```

Si falla desde el servidor, el problema es de red, no de Docker.

### Error de base de datos

```bash
docker exec clockcontrol python -c "
from clockcontrol.config.settings import get_settings
from clockcontrol.database.connection import DatabaseConnection
s = get_settings()
db = DatabaseConnection(s.database.to_dict())
db.ensure_tables_exist()
print('Conexion OK')
"
```

Si falla, revisar las credenciales en `database.ini`.

### El contenedor se reinicia constantemente

```bash
# Ver la razon
docker logs --tail 30 clockcontrol

# Ver el codigo de salida
docker inspect clockcontrol --format '{{.State.ExitCode}}'
```

### Verificar que el contenedor tiene acceso de red

```bash
# Debe mostrar la misma red que el servidor (network: host)
docker exec clockcontrol ip addr
```

---

## Resumen: Comando de produccion

```bash
# 1. Crear database.ini en el servidor
nano /etc/clockcontrol/database.ini

# 2. Ejecutar
docker run -d \
  --name clockcontrol \
  --restart unless-stopped \
  --network host \
  -v /etc/clockcontrol/database.ini:/app/database.ini:ro \
  -e RUN_MODE=all \
  -e CRON_INTERVAL=5 \
  clockcontrol:2.0

# 3. Verificar
docker ps
docker logs -f clockcontrol
```

---

*Documento generado para clockControl v2.0 - SEGIP Bolivia - Febrero 2026*
