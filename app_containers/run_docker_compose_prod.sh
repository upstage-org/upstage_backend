#!/bin/bash

export DOCKER_CLIENT_DEBUG=1
export HARDCODED_HOSTNAME=upstage.live

set -a

cp -r ../pyproject.toml /app_code
cp -r ../src /app_code
cp -r ../alembic /app_code
cp -r ../scripts /app_code
cp -r ../dashboard/demo /app_code
cp -r ../requirements.txt /app_code
cp -r ../pyproject.toml /app_code
cp -r ../migration_scripts /app_code
chown -R 1001:0 /app_code
chmod -R g+rwX /app_code

docker compose -f ./docker-compose-prod.yaml -p upstage-backend-prod down
#docker compose rm -f
docker compose -f ./docker-compose-prod.yaml -p upstage-backend-prod up -d
sleep 5
docker compose -f ./docker-compose-prod.yaml -p upstage-backend-prod ps
