#!/bin/sh
set -e

cd /app
export PYTHONPATH=${PYTHONPATH:-/app}

echo "Running auth-svc migrations..."
alembic upgrade head

echo "Starting auth-svc..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8006
