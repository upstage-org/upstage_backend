#!/bin/bash

set -a

SITE=dev
DOCKER_CLIENT_DEBUG=1
HARDCODED_HOSTNAME=${SITE}.upstage.live
APP_PORT=9090
APP_USER=1000
APP_GROUP=1000

sudo mkdir -p "/app_code_${SITE}/uploads"
sudo chown -R "${APP_USER}:${APP_GROUP}" "/app_code_${SITE}/uploads"

docker compose -f docker-compose.yaml -p docker-backend-${SITE} down --remove-orphans
docker compose rm -f
docker compose -f docker-compose.yaml -p docker-backend-${SITE} up --build -d
docker compose -f docker-compose.yaml -p docker-backend-${SITE} ps
