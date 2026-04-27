#!/bin/sh
set -e

cd /usr/app

echo "Running Alembic migrations..."
uv run alembic -c ./scripts/alembic.ini upgrade heads

echo "Starting Uvicorn server..."
uvicorn upstage_backend.main:app \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --host 0.0.0.0 \
    --port 3000
