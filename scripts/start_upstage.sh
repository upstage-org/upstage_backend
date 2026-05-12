#!/bin/sh
# Container entry point for the upstage_backend FastAPI service.
#
# No PYTHONPATH manipulation: `upstage_backend` is `pip install -e .`-d
# into ${VIRTUAL_ENV} during the Docker build (see
# app_containers/docker-compose.yaml `x-common-build` runtime stage), so
# the `uvicorn upstage_backend.main:app` invocation below resolves the
# package via the venv's site-packages, with no sys.path headers needed.
set -e
cd /usr/app
VENV="${VIRTUAL_ENV:-/usr/app/.venv}"
export VIRTUAL_ENV="$VENV"
export PATH="${VENV}/bin:${PATH}"

# Alembic is intentionally NOT run here. Migrations are handled exactly
# once by the `upstage_db_migrate` one-shot service in
# app_containers/docker-compose.yaml; this service depends_on it with
# `service_completed_successfully`, so by the time we get here the schema
# is at heads. Running it again would create needless `LOCK TABLE
# alembic_version` contention.

echo "Starting Uvicorn server..."
exec uvicorn upstage_backend.main:app \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --host 0.0.0.0 \
    --port 3000
