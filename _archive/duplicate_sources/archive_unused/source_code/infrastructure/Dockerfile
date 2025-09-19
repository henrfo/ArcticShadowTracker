# Arctic Shadow Tracker - Production Docker Image
# Multi-stage build for optimized production deployment

# Stage 1: Base image with system dependencies
FROM python:3.9-slim-bullseye as base

# Install system dependencies for geospatial processing and monitoring
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    libspatialindex-dev \
    gcc \
    g++ \
    curl \
    wget \
    cron \
    supervisor \
    procps \
    htop \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_DATA=/usr/share/gdal
ENV PROJ_LIB=/usr/share/proj

# Stage 2: Dependencies installation
FROM base as dependencies

WORKDIR /app

# Copy requirements first for better caching
COPY config/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir prometheus-client flask requests-oauthlib

# Stage 3: Application
FROM dependencies as application

# Create non-root user for security with proper permissions
RUN useradd --create-home --shell /bin/bash --uid 1000 arctic && \
    mkdir -p /app/data /app/outputs /app/logs /app/config /app/tmp && \
    mkdir -p /app/data/operational/daily /app/data/operational/historical /app/data/operational/cumulative /app/data/operational/latest && \
    mkdir -p /app/data/ais /app/data/satellite /app/data/cables && \
    mkdir -p /app/outputs/daily_reports /app/outputs/operational_reports /app/outputs/visualizations && \
    chown -R arctic:arctic /app

# Copy application code
COPY --chown=arctic:arctic . /app/

# Set up cron for arctic user
COPY --chown=root:root infrastructure/deploy/crontab-production /etc/cron.d/arctic-tracker
RUN chmod 0644 /etc/cron.d/arctic-tracker && \
    crontab -u arctic /etc/cron.d/arctic-tracker

# Copy supervisor configuration
COPY infrastructure/deploy/supervisord.conf /etc/supervisor/conf.d/arctic-tracker.conf

# Set Python path and environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DATA_PERSISTENCE_ENABLED=1
ENV VISUALIZATION_ENABLED=1

# Switch to arctic user
USER arctic

# Create volume mount points with proper permissions
VOLUME ["/app/data", "/app/outputs", "/app/logs", "/app/config"]

# Enhanced health check with multiple validation points
HEALTHCHECK --interval=60s --timeout=30s --start-period=180s --retries=3 \
    CMD python -c "from infrastructure.deploy.health_monitor import docker_health_check; docker_health_check()" || exit 1

# Expose ports for API and monitoring
EXPOSE 8000 9090

# Use supervisor for process management in production
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/arctic-tracker.conf"]