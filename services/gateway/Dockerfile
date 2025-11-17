# services/gateway/Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app

# Minimizar interacción y evitar sugerencias de locales durante instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias necesarias para compilar ruedas (preferir no-install-recommends)
RUN apt-get -o Acquire::Retries=3 update \
 && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
     gcc \
     build-essential \
     python3-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copiar requirements y generar ruedas en /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Copiar el código (opcional para procesos de build que lo requieran)
COPY . /app

FROM python:3.12-slim
WORKDIR /app

# Evitar interacción en la etapa final también
ENV DEBIAN_FRONTEND=noninteractive

# Copiar ruedas y requirements desde el builder
COPY --from=builder /wheels /wheels
COPY requirements.txt .

# Instalar dependencias Python desde las ruedas (no index)
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copiar código de la aplicación desde el builder
COPY --from=builder /app /app

# Exponer puerto y comando de inicio
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
