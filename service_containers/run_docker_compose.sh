#!/bin/bash

set -a

export POSTGRES_PASSWORD=POSTGRES_PASSWORD
export MONGO_INITDB_ROOT_PASSWORD=MONGO_PASSWORD

docker compose up -d
sleep 5
docker compose ps
