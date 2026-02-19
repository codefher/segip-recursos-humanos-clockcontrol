# Auditoria de Codigo - clockControl v2.0

> Revision completa del proyecto
> Fecha: 18 de Febrero 2026

---

## Resumen

| Severidad | Cantidad |
|-----------|----------|
| CRITICO   | 2        |
| MEDIO     | 8        |
| BAJO      | 10       |

---

## CRITICOS (Resolver hoy)

### 1. Credenciales de BD expuestas en el repositorio

- **Archivo:** `database.ini`
- **Problema:** El archivo contiene credenciales reales (`password=Calidad2021`) y fue commiteado al repositorio git. Aunque esta en `.gitignore`, ya esta en el historial de git.
- **Solucion:**
  1. Rotar la contrasena de la base de datos inmediatamente
  2. Eliminar del historial de git:
     ```bash
     git filter-branch --tree-filter 'rm -f database.ini' HEAD
     ```
  3. Verificar que `.gitignore` incluya `database.ini`

---

### 2. Credenciales visibles en historial de git

- **Archivo:** historial de git
- **Problema:** Las credenciales (`usr_recursos_humanos` / `Calidad2021`) quedaron registradas en commits anteriores.
- **Solucion:** Rotar credenciales y limpiar historial con `git filter-branch` o BFG Repo-Cleaner.

---

## MEDIO (Resolver esta semana)

### 3. ID de reloj hardcodeado (4570) en stored procedure

- **Archivo:** `clockcontrol/database/repositories.py` - linea 117
- **Problema:** Se pasa `4570` como primer parametro fijo al stored procedure `set_attendance_info_clock`. Deberia ser el ID real del reloj que se esta procesando.
- **Codigo actual:**
  ```python
  cur.callproc("rrhh.set_attendance_info_clock", (4570, marks_json))
  ```
- **Solucion:**
  ```python
  cur.callproc("rrhh.set_attendance_info_clock", (clock_id, marks_json))
  ```
  Pasar el `clock.id_reloj_bio` desde el metodo que llama.

---

### 4. No se valida el codigo de respuesta del stored procedure

- **Archivo:** `clockcontrol/database/repositories.py` - lineas 114-125
- **Problema:** El SP retorna `(codRespuesta, mensaje, cantidadInsertados)` pero solo se usa `cantidadInsertados`. Si `codRespuesta = -100` (error), se ignora silenciosamente.
- **Codigo actual:**
  ```python
  result = cur.fetchone()
  if result:
      inserted = result[2] if len(result) > 2 else 0
  ```
- **Solucion:**
  ```python
  result = cur.fetchone()
  if result:
      cod_respuesta = result[0]
      mensaje = result[1]
      inserted = result[2] if len(result) > 2 else 0
      if cod_respuesta < 0:
          logger.error(f"Error SP [{cod_respuesta}]: {mensaje}")
      else:
          logger.info(f"Marcajes guardados: {inserted} nuevos")
      return inserted
  ```

---

### 5. Consulta booleana inconsistente en repositorio

- **Archivo:** `clockcontrol/database/repositories.py` - linea 60
- **Problema:** `get_all_active()` usa `activo = 1` hardcodeado en el query, mientras que `get_by_ip()` usa query parametrizado con `%s`. Deberia ser consistente.
- **Solucion:** Usar query parametrizado:
  ```python
  query = "SELECT * FROM rrhh.reloj_biometrico WHERE activo = %s"
  cur.execute(query, (1,))
  ```

---

### 6. Sin validacion JSON antes de enviar al stored procedure

- **Archivo:** `clockcontrol/database/repositories.py` - linea 104
- **Problema:** `save_marks()` recibe un string JSON pero no valida que sea JSON valido antes de pasarlo al SP. Si el JSON esta malformado, el error sera confuso.
- **Solucion:**
  ```python
  import json

  def save_marks(self, marks_json: str) -> int:
      try:
          json.loads(marks_json)  # Validar
      except json.JSONDecodeError as e:
          logger.error(f"JSON invalido: {e}")
          return 0
      # ... resto del metodo
  ```

---

### 7. Sin reintentos en conexion al dispositivo biometrico

- **Archivo:** `clockcontrol/core/device.py` - lineas 115-126
- **Problema:** La conexion al reloj ZKTeco se intenta una sola vez. Si la red esta temporalmente lenta, falla inmediatamente sin reintentar.
- **Solucion:** Implementar reintentos con backoff:
  ```python
  def connect(self, retries=3, delay=2):
      for attempt in range(retries):
          try:
              # ... intentar conexion
              return True
          except Exception as e:
              if attempt < retries - 1:
                  logger.warning(f"Intento {attempt+1} fallido, reintentando en {delay}s...")
                  time.sleep(delay)
              else:
                  logger.error(f"Fallo despues de {retries} intentos: {e}")
                  return False
  ```

---

### 8. Condicion de carrera en cron (ejecuciones superpuestas)

- **Archivo:** `docker-entrypoint.sh` - lineas 50-61
- **Problema:** Si el procesamiento de relojes tarda mas que el intervalo del cron, pueden ejecutarse multiples instancias simultaneamente.
- **Solucion:** Agregar lock file al comando del cron:
  ```bash
  LOCK="/tmp/clockcontrol.lock"
  CLOCK_CMD="flock -n $LOCK $CLOCK_CMD"
  ```

---

### 9. Parsing de marcajes fragil

- **Archivo:** `clockcontrol/core/attendance.py` - lineas 104-122
- **Problema:** El parsing asume un formato exacto `"Attendance <carnet> : <YYYY-MM-DD> <HH:MM:SS> <status>"`. Si el dispositivo retorna un formato ligeramente diferente, el marcaje se descarta silenciosamente (retorna `None` sin log).
- **Solucion:** Agregar logs de warning cuando el formato no coincide:
  ```python
  if len(parts) < 5:
      logger.warning(f"Formato inesperado ({len(parts)} partes): {data_str[:100]}")
      return None
  ```

---

### 10. Healthcheck de Docker debil

- **Archivo:** `Dockerfile` - linea 58
- **Problema:** El healthcheck solo verifica que Python puede importar `__version__`, no que el sistema realmente funcione (conexion a BD, acceso a red).
- **Solucion:**
  ```dockerfile
  HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
      CMD python -c "from clockcontrol import __version__; print(__version__)" \
          && test -f /app/database.ini \
          || exit 1
  ```

---

## BAJO (Resolver cuando se pueda)

### 11. Import no utilizado

- **Archivo:** `clockcontrol/core/attendance.py` - linea 10
- **Problema:** Se importa `ValidationError` pero nunca se usa.
- **Solucion:** Eliminar el import.

---

### 12. Logging solo a archivo, no a consola

- **Archivo:** `clockcontrol/config/settings.py` - lineas 87-95
- **Problema:** Solo tiene `FileHandler`, no `StreamHandler`. En Docker, `docker logs` no muestra los logs internos de la aplicacion (solo los del cron).
- **Nota:** Esto se modifico intencionalmente para evitar duplicacion de logs con cron. Evaluar si conviene agregar StreamHandler solo cuando NO se ejecuta via cron.

---

### 13. Tipo de password incorrecto

- **Archivo:** `clockcontrol/config/settings.py` - linea 48
- **Problema:** `default_password: int = 0` deberia ser `str` ya que las contrasenas de dispositivos ZK pueden contener caracteres no numericos.
- **Solucion:** Cambiar a `default_password: str = "0"`

---

### 14. Sin validacion de formato IP en CLI

- **Archivo:** `clockcontrol/cli.py` - lineas 285-289
- **Problema:** El argumento `--address` acepta cualquier string sin validar que sea una IP valida.
- **Solucion:** Agregar validacion basica.

---

### 15. Excepcion sin encadenamiento (from e)

- **Archivo:** `clockcontrol/database/connection.py` - linea 56
- **Problema:** `raise DatabaseError(...)` sin `from e`, lo que pierde el traceback original.
- **Solucion:**
  ```python
  raise DatabaseError(f"Error de base de datos: {e}") from e
  ```

---

### 16. Excepcion silenciada en desconexion

- **Archivo:** `clockcontrol/core/device.py` - linea 132
- **Problema:** `except Exception: pass` - errores de desconexion se ignoran completamente.
- **Solucion:**
  ```python
  except Exception as e:
      logger.debug(f"Error al desconectar de {self.ip}: {e}")
  ```

---

### 17. Rotacion de logs no configurada

- **Archivo:** `docker-entrypoint.sh`
- **Problema:** Los logs se escriben indefinidamente a `/app/logs/clockcontrol.log` sin rotacion. En produccion a largo plazo, el archivo crecera sin limite.
- **Solucion:** Usar `RotatingFileHandler` en Python o configurar `logrotate` en el contenedor.

---

### 18. Error en install.sh

- **Archivo:** `install.sh` - linea 83
- **Problema:** La verificacion de pyzk intenta importar de forma incorrecta.
- **Solucion:** Cambiar a `python -c "import zk"`

---

### 19. Falta archivo .env.example

- **Problema:** No existe un archivo de ejemplo con todas las variables de entorno documentadas.
- **Solucion:** Crear `.env.example` con las variables y sus valores por defecto.

---

### 20. Version de Python inconsistente

- **Archivo:** `Dockerfile` vs `pyproject.toml`
- **Problema:** Dockerfile usa `python:3.11-slim` pero pyproject.toml dice `>=3.9`. No es un error pero podria causar confusion.
- **Solucion:** Documentar que la version recomendada es 3.11.

---

## Prioridades de accion

```
HOY:
  [1] Rotar contrasena de BD (Calidad2021 esta expuesta)
  [2] Limpiar historial de git

ESTA SEMANA:
  [3] Corregir ID hardcodeado 4570 → clock_id dinamico
  [4] Validar codigo de respuesta del stored procedure
  [6] Validar JSON antes de enviar al SP
  [8] Agregar lock file para evitar ejecuciones superpuestas

PROXIMO SPRINT:
  [7]  Reintentos en conexion al dispositivo
  [9]  Mejorar parsing de marcajes con logs
  [17] Configurar rotacion de logs
  Resto de items BAJO
```

---

*Auditoria generada para clockControl v2.0 - SEGIP Bolivia - Febrero 2026*
