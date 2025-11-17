# services/auth-svc/Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app

# Minimizar interacción y evitar prompts
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias necesarias para compilar ruedas (usar no-install-recommends y reintentos)
RUN apt-get -o Acquire::Retries=3 update \
 && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    gcc \
    build-essential \
    python3-dev \
    libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copiar requirements y generar ruedas en /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt || true

# Copiar código (necesario para entrypoint/script packaging)
COPY . /app

FROM python:3.12-slim
WORKDIR /app

# Minimizar interacción en la etapa final
ENV DEBIAN_FRONTEND=noninteractive

# Instalar cliente psql en la imagen final (pequeña dependencia runtime)
RUN apt-get -o Acquire::Retries=3 update \
 && apt-get -o Acquire::Retries=3 install -y --no-install-recommends postgresql-client \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copiar ruedas y requirements desde el builder (si se generaron)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt || pip install --no-cache-dir -r requirements.txt

# Copiar el código de la app desde builder
COPY --from=builder /app /app

# Corregir finales CRLF que pueden aparecer cuando se construye desde Windows
RUN sed -i 's/\r$//' /app/entrypoint.sh || true

# Preparar entrypoint para correr migraciones automáticamente
RUN chmod +x /app/entrypoint.sh

# Exponer puerto y entrypoint
EXPOSE 8006
ENTRYPOINT ["/app/entrypoint.sh"]
