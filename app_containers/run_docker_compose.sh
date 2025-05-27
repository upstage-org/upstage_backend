#!/bin/bash

export DOCKER_CLIENT_DEBUG=1

set -a

cp -r ../src /app_code
cp -r ../alembic /app_code
cp -r ../scripts /app_code
cp -r ../dashboard/demo /app_code
cp -r ../requirements.txt /app_code
cp -r ../migration_scripts /app_code

docker compose down
docker compose rm -f
docker compose up -d --build
sleep 5
docker compose ps
