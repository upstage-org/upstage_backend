#!/bin/sh
set -e
cd /usr/app
VENV="${VIRTUAL_ENV:-/usr/app/.venv}"
export VIRTUAL_ENV="$VENV"
export PATH="${VENV}/bin:${PATH}"
export PYTHONPATH="/usr/app/src${PYTHONPATH:+:$PYTHONPATH}"

echo "Running Alembic migrations..."
python -m alembic -c ./scripts/alembic.ini upgrade heads

echo "Starting Uvicorn server..."
exec uvicorn upstage_backend.main:app \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --host 0.0.0.0 \
    --port 3000
