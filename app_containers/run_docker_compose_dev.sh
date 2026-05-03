#!/bin/bash

set -a

SITE=dev
DOCKER_CLIENT_DEBUG=1
HARDCODED_HOSTNAME=${SITE}.upstage.live
APP_ROOT=/app_code_${SITE}
APP_USER=1000
APP_GROUP=1000

sudo cp -r ../pyproject.toml $APP_ROOT
sudo cp -r ../uv.lock $APP_ROOT
sudo cp -r ../src $APP_ROOT
sudo cp -r ../alembic $APP_ROOT
sudo cp -r ../scripts $APP_ROOT
sudo cp -r ../dashboard/demo $APP_ROOT
sudo cp -r ../migration_scripts $APP_ROOT

currwd=`pwd`
cd $APP_ROOT
sudo ${HOME}/.local/bin/uv sync --no-dev 
sudo chown -R $APP_USER:$APP_GROUP $APP_ROOT
cd $currwd

docker compose -f docker-compose.yaml -p docker-backend-${SITE} down --remove-orphans
docker compose rm -f
docker compose -f docker-compose.yaml -p docker-backend-${SITE} up --build -d
docker compose -f docker-compose.yaml -p docker-backend-${SITE} ps
