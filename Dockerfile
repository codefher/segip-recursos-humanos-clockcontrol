# clockControl - Sistema de Control de Asistencia SEGIP
# Imagen Docker para ejecucion en contenedor

FROM python:3.11-slim

# Metadatos
LABEL maintainer="SEGIP <desarrollo@segip.gob.bo>"
LABEL description="Sistema de control de asistencia - Extraccion de marcajes ZKTeco"
LABEL version="2.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CLOCK_IP="10.10.24.48"
ENV CLOCK_PORT="4370"
ENV CLOCK_PASSWORD="0"
ENV RUN_MODE="single"

# Directorio de trabajo
WORKDIR /app

# Copiar archivos de configuracion primero (mejor cache de capas)
COPY pyproject.toml requirements.txt ./
COPY tmp.database.ini ./database.ini

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar codigo fuente
COPY clockcontrol/ ./clockcontrol/

# Instalar paquete en modo editable
RUN pip install --no-cache-dir -e .

# Usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash clockuser \
    && chown -R clockuser:clockuser /app
USER clockuser

# Puerto del reloj biometrico (informativo)
EXPOSE 4370/udp

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from clockcontrol import __version__; print(__version__)" || exit 1

# Comando por defecto
# Modo individual: docker run -e CLOCK_IP=192.168.1.201 clockcontrol
# Modo masivo: docker run -e RUN_MODE=all clockcontrol
CMD ["sh", "-c", "if [ \"$RUN_MODE\" = 'all' ]; then python -m clockcontrol all; else python -m clockcontrol single --address $CLOCK_IP --port $CLOCK_PORT --password $CLOCK_PASSWORD; fi"]
