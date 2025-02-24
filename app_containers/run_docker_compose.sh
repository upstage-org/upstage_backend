#!/bin/bash

set -a

docker compose down
docker compose rm -f
docker compose up -d
sleep 5
docker compose ps
