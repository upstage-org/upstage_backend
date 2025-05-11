#!/bin/bash

set -a

cp -r ../src /app_code
cp -r ../alembic /app_code
cp -r ../scripts /app_code
cp -r ../dashboard/demo /app_code
cp -r ../requirements.txt /app_code
cp -r ../startup.sh /app_code

export DOCKER_CLIENT_DEBUG=1

docker compose down
docker compose rm -f
docker compose up -d
sleep 5
docker compose ps
