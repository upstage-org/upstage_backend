#!/bin/bash

set -a

export POSTGRES_PASSWORD=REPLACE_POSTGRES_PASSWORD
export MONGO_INITDB_ROOT_PASSWORD=REPLACE_MONGO_PASSWORD

docker compose up -d
sleep 5
docker compose ps
