FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dependencias del sistema (Postgres / builds)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar proyecto completo (incluye pyproject.toml)
COPY . .

# Instalar el proyecto desde pyproject.toml
RUN pip install --no-cache-dir -e .

# Script de arranque
COPY backend/startup.sh /app/backend/startup.sh
RUN chmod +x /app/backend/startup.sh

EXPOSE 8000

ENTRYPOINT ["/app/backend/startup.sh"]
