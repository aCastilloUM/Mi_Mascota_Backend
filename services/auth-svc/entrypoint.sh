#!/bin/sh
set -e

cd /app
export PYTHONPATH=${PYTHONPATH:-/app}

echo "Running auth-svc migrations..."
# If DB_SCHEMA is set, force the session search_path so Alembic creates/reads
# alembic_version inside the desired schema instead of the default schema.
if [ -n "${DB_SCHEMA}" ]; then
	export PGOPTIONS="-c search_path=${DB_SCHEMA}"
	echo "Using search_path=${DB_SCHEMA} for migrations"
fi

alembic upgrade head

echo "Starting auth-svc..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8006
