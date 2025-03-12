#!/bin/bash

set -a

export DOCKER_CLIENT_DEBUG=1

docker compose down
docker compose rm -f
docker compose up -d
sleep 5
docker compose ps
