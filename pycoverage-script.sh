#!/bin/sh
export PGPASSWORD="postgres"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
psql -h localhost -p 5432 -U postgres -c "DROP DATABASE IF EXISTS upstage_test;"
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE upstage_test;"
alembic -c scripts/alembic.ini upgrade heads
coverage run -m pytest
