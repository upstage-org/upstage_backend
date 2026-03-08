#!/bin/bash

set -a

export DOCKER_CLIENT_DEBUG=1
export HARDCODED_HOSTNAME=dev.upstage.live

cp -r ../src /app_code_dev
cp -r ../alembic /app_code_dev
cp -r ../scripts /app_code_dev
cp -r ../dashboard/demo /app_code_dev
cp -r ../requirements.txt /app_code_dev
cp -r ../migration_scripts /app_code_dev

docker compose -f docker-compose-dev.yaml -p docker-backend-dev down --remove-orphans
#docker compose rm -f
docker compose -f docker-compose-dev.yaml -p docker-backend-dev up -d --build
sleep 5
docker compose ps
