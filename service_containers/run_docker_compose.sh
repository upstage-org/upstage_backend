#!/bin/bash

set -a

export POSTGRES_PASSWORD=ickk2lB4oxhT
export MONGO_INITDB_ROOT_PASSWORD=seAgoF7aP4AU

docker compose up -d
sleep 5
docker compose ps
