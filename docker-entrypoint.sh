#!/bin/bash
#
# clockControl - Docker Entrypoint
# Configura el cron y mantiene el contenedor corriendo
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
echo "Intervalo del cron: cada $CRON_INTERVAL minutos"
echo ""

# Construir el comando segun el modo
if [ "$RUN_MODE" = "single" ]; then
    CLOCK_CMD="cd /app && /usr/local/bin/python -m clockcontrol single --address $CLOCK_IP --port $CLOCK_PORT --password $CLOCK_PASSWORD"
    echo "Reloj configurado: $CLOCK_IP:$CLOCK_PORT"
else
    CLOCK_CMD="cd /app && /usr/local/bin/python -m clockcontrol all"
    echo "Procesando todos los relojes activos"
fi

echo ""

# Crear el cron job dinamicamente con las variables de entorno
echo "*/$CRON_INTERVAL * * * * $CLOCK_CMD >> /app/logs/clockcontrol.log 2>&1" > /etc/cron.d/clockcontrol
echo "" >> /etc/cron.d/clockcontrol

# Dar permisos al cron
chmod 0644 /etc/cron.d/clockcontrol
crontab /etc/cron.d/clockcontrol

echo "Cron configurado: cada $CRON_INTERVAL minutos"
echo ""

# Ejecutar una primera vez inmediatamente para verificar que funciona
echo "Ejecutando primera extraccion de prueba..."
echo ""
eval $CLOCK_CMD 2>&1 | tee -a /app/logs/clockcontrol.log
echo ""
echo "=============================================="
echo "  Cron activo. Logs en /app/logs/clockcontrol.log"
echo "=============================================="

# Iniciar cron en primer plano y seguir los logs
cron
exec tail -f /app/logs/clockcontrol.log
