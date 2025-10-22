# services/auth-svc/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Corregir finales CRLF que pueden aparecer cuando se construye desde Windows
RUN sed -i 's/\r$//' /app/entrypoint.sh || true

# Preparar entrypoint para correr migraciones automáticamente
RUN chmod +x /app/entrypoint.sh

# Exponer puerto
EXPOSE 8006

# Ejecutar script que corre alembic y luego arranca uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]
