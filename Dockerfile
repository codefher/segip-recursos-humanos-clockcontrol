# clockControl - Sistema de Control de Asistencia SEGIP
# Imagen Docker con cron interno para ejecucion automatica

FROM python:3.11-slim

# Metadatos
LABEL maintainer="SEGIP <desarrollo@segip.gob.bo>"
LABEL description="Sistema de control de asistencia - Extraccion de marcajes ZKTeco"
LABEL version="2.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Intervalo del cron en minutos (default: cada 5 minutos)
ENV CRON_INTERVAL=5

# Variables para modo individual (si se usa RUN_MODE=single)
ENV CLOCK_IP="10.10.24.48"
ENV CLOCK_PORT="4370"
ENV CLOCK_PASSWORD="0"
ENV RUN_MODE="all"

# Directorio de trabajo
WORKDIR /app

# Copiar archivos de configuracion primero (mejor cache de capas)
COPY pyproject.toml requirements.txt ./

# Instalar dependencias del sistema (cron + ping)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar codigo fuente
COPY clockcontrol/ ./clockcontrol/
COPY scripts/ ./scripts/

# Instalar paquete
RUN pip install --no-cache-dir -e .

# Dar permisos a scripts
RUN chmod +x scripts/*.sh

# Copiar script de inicio
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Crear directorio de logs
RUN mkdir -p /app/logs

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from clockcontrol import __version__; print(__version__)" \
        && test -f /app/database.ini \
        || exit 1

# Entrypoint configura el cron y arranca
ENTRYPOINT ["/docker-entrypoint.sh"]
