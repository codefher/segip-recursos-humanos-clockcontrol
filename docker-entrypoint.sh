#!/bin/bash
#
# clockControl - Docker Entrypoint
# Soporta dos modos de intervalo:
#   - CRON_INTERVAL (minutos, usa cron)       -> para produccion
#   - LOOP_INTERVAL_SECONDS (segundos, usa loop) -> para alta frecuencia
#

set -e

echo "=============================================="
echo "  clockControl v2.0 - Docker"
echo "=============================================="
echo ""

# Verificar que database.ini existe
if [ ! -f /app/database.ini ]; then
    echo "ERROR: No se encontro /app/database.ini"
    echo ""
    echo "Debes montar el archivo de configuracion:"
    echo "  docker run -v /ruta/a/database.ini:/app/database.ini ..."
    echo ""
    exit 1
fi

echo "Modo de ejecucion: $RUN_MODE"

# Construir el comando segun el modo
if [ "$RUN_MODE" = "single" ]; then
    CLOCK_CMD="cd /app && /usr/local/bin/python -m clockcontrol single --address $CLOCK_IP --port $CLOCK_PORT --password $CLOCK_PASSWORD"
    echo "Reloj configurado: $CLOCK_IP:$CLOCK_PORT"
else
    CLOCK_CMD="cd /app && /usr/local/bin/python -m clockcontrol all"
    echo "Procesando todos los relojes activos"
fi

echo ""

# Ejecutar primera extraccion de prueba
echo "Ejecutando primera extraccion..."
echo ""
eval $CLOCK_CMD 2>&1 | tee -a /app/logs/clockcontrol.log
echo ""

# Decidir modo de ejecucion: loop (segundos) o cron (minutos)
if [ -n "$LOOP_INTERVAL_SECONDS" ] && [ "$LOOP_INTERVAL_SECONDS" -gt 0 ] 2>/dev/null; then
    # === MODO LOOP (alta frecuencia, cada N segundos) ===
    echo "=============================================="
    echo "  Loop activo: cada $LOOP_INTERVAL_SECONDS segundos"
    echo "=============================================="
    echo ""

    while true; do
        sleep "$LOOP_INTERVAL_SECONDS"
        echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---"
        eval $CLOCK_CMD 2>&1 | tee -a /app/logs/clockcontrol.log
        echo ""
    done
else
    # === MODO CRON (produccion, cada N minutos) ===
    echo "Intervalo del cron: cada $CRON_INTERVAL minutos"
    echo ""

    # Crear el cron job con flock para evitar ejecuciones superpuestas
    echo "*/$CRON_INTERVAL * * * * flock -n /tmp/clockcontrol.lock /bin/bash -c '$CLOCK_CMD' >> /app/logs/clockcontrol.log 2>&1" > /etc/cron.d/clockcontrol
    echo "" >> /etc/cron.d/clockcontrol

    chmod 0644 /etc/cron.d/clockcontrol
    crontab /etc/cron.d/clockcontrol

    echo "=============================================="
    echo "  Cron activo. Logs en /app/logs/clockcontrol.log"
    echo "=============================================="

    # Iniciar cron y seguir los logs
    cron
    exec tail -f /app/logs/clockcontrol.log
fi
