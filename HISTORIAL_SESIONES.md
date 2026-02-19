# Historial de Sesiones de Desarrollo - clockControl v2.0

> Este documento registra el progreso de desarrollo para continuidad entre sesiones.

---

## Sesion 1 y 2 - 13 de Febrero 2026

### Lo que se hizo:
1. **Registro de huella en ZKTeco** - El campo "ID de Usuario" debe coincidir con el carnet (ej: 100400327)
2. **Primera prueba exitosa** - Marcaje extraido del reloj y guardado en PostgreSQL (ID: 117654)
3. **Bug fix critico** - `repositories.py:117` parametros del SP estaban como array en vez de separados
4. **Configuracion de cron** - `*/5 * * * *` ejecuta `scripts/run_all.sh`
5. **Fix logging duplicado** - Removido StreamHandler de settings.py
6. **Documentacion** - Creado `GUIA_DESPLIEGUE_PRODUCCION.md`

### Dockerizacion:
1. Reescrito `Dockerfile` con soporte de cron interno
2. Creado `docker-entrypoint.sh`
3. Creado `docker-compose.yml`
4. Imagen construida y probada exitosamente
5. Creado `GUIA_DOCKER.md` y `GUIA_DOCKER_RUN.md`

### Investigacion del proceso misterioso:
- Descubierto que `"exist ping"` viene de `10.0.50.12` cada minuto
- Backend .NET (`rrhh-backend-calidad`) ejecuta `GetMarcacionesRelojMasivamenteHostedService`
- Pero este backend NO conecta al reloj fisico (codigo comentado)
- Solo llama `p_asistencia_insert_all_attendance` (mueve person_marks → fun_asistencia)
- Los `python run.py` en .12 son de `prueba-vida`, no de clockControl
- El cron en .12 esta comentado
- **PENDIENTE:** Alguien sigue insertando en `person_marks` - no identificado

---

## Sesion 3 - 18-19 de Febrero 2026

### Prueba con loop de alta frecuencia:
1. Modificado `docker-entrypoint.sh` para soportar `LOOP_INTERVAL_SECONDS`
2. Con loop de 10s, clockControl guardo **3 marcajes** antes que el proceso misterioso
3. Confirmado que el proyecto funciona correctamente

### Auditoria de codigo completa:
- Revisados todos los archivos Python, Docker, SQL, scripts
- Documentados 20 hallazgos en `AUDITORIA_CODIGO.md`
- 2 CRITICOS (credenciales), 8 MEDIO, 10 BAJO

### Correcciones aplicadas (18 de 20):

| # | Correccion | Archivo |
|---|-----------|---------|
| 3 | ID hardcodeado 4570 → clock.id dinamico | repositories.py, cli.py |
| 4 | Validar codigo respuesta del SP (-100 = error) | repositories.py |
| 5 | Query parametrizado `activo = %s` | repositories.py |
| 6 | Validar JSON antes de enviar al SP | repositories.py |
| 7 | Reintentos en conexion al dispositivo (2 intentos, 2s delay) | device.py |
| 8 | Lock file (flock) para evitar ejecuciones superpuestas | docker-entrypoint.sh |
| 9 | Parsing mejorado con validacion de fecha/hora | attendance.py |
| 10 | Healthcheck mejorado (verifica database.ini) | Dockerfile |
| 11 | Import no usado ValidationError eliminado | attendance.py |
| 13 | Password tipo int → str (compatible con pyzk) | settings, models, cli, device |
| 14 | Validacion de formato IP en CLI | cli.py |
| 15 | Exception chaining (from e) | connection.py |
| 16 | Excepcion silenciada → log debug | device.py |
| 17 | Rotacion de logs (RotatingFileHandler 10MB x 5) | settings.py |
| 18 | Fix verificacion pyzk en install.sh | install.sh |
| 19 | Creado .env.example | .env.example |

### Bug fix adicional:
- `docker-entrypoint.sh` - flock necesita envolver comando con `/bin/bash -c '...'`
- Sin esto, el cron ejecutaba `flock -n /tmp/lock cd /app` que fallaba silenciosamente

### No corregidos (usuario gestiona):
- #1 y #2: Credenciales en repositorio (usuario lo gestiona directamente)

### Trigger de auditoria:
- SQL listo en `sql/audit_trigger_person_marks.sql`
- Necesita ser ejecutado por DBA con permisos CREATE en schema rrhh
- Registra IP, usuario, PID de cada INSERT en person_marks
- Servira para identificar el proceso misterioso

---

## Pendientes para proxima sesion:

1. **Identificar proceso misterioso** - Ejecutar trigger de auditoria y consultar `person_marks_audit`
2. **Credenciales** - Usuario debe rotar password y limpiar historial git
3. **Produccion** - Cambiar de LOOP_INTERVAL_SECONDS=10 a CRON_INTERVAL=5
4. **Probar reintentos** - Verificar que los 2 intentos de conexion funcionan con relojes inestables

---

*Documento actualizado: 19 de Febrero 2026*
