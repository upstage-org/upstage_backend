#!/bin/bash

set -a

# Containers run as the host user (see docker-compose-dev.yaml). Exporting these
# here makes the compose ${HOST_UID}/${HOST_GID} interpolation deterministic
# without anyone having to hand-edit .env.
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"

export DOCKER_CLIENT_DEBUG=1
export HARDCODED_HOSTNAME=testing.upstage.live

thisdir=`pwd`
cd .. && uv sync --no-dev && cd $thisdir

cp -r ../pyproject.toml /app_code_dev
cp -r ../uv.lock /app_code_dev
cp -r ../src /app_code_dev
cp -r ../alembic /app_code_dev
cp -r ../scripts /app_code_dev
cp -r ../dashboard/demo /app_code_dev
cp -r ../requirements.txt /app_code_dev
cp -r ../migration_scripts /app_code_dev

docker compose -f docker-compose-dev.yaml -p docker-backend-dev down --remove-orphans
docker compose rm -f
docker compose -f docker-compose-dev.yaml -p docker-backend-dev up --build -d
docker compose -f docker-compose-dev.yaml -p docker-backend-dev ps
