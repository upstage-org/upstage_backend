#!/bin/bash

set -a

export POSTGRES_PASSWORD=bvTPJ07p37d
export MONGO_INITDB_ROOT_PASSWORD=eCGhS5vHruyW

docker compose up -d
sleep 5
docker compose ps
