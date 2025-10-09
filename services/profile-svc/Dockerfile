FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./

# ✅ Usamos el cache mount de pip y NO usamos --no-cache-dir para que realmente cachee
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -U pip setuptools wheel && \
    python -m pip install -r requirements.txt --prefer-binary -v

COPY app /app/app
COPY alembic.ini /app/alembic.ini

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
