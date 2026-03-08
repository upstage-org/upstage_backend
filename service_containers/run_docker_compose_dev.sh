#!/bin/bash

# This file is generated. Do not change the generated copy. It will be
# overwritten.

set -a

export POSTGRES_PASSWORD=t3zNqfh5lLcx
export MONGO_INITDB_ROOT_PASSWORD=c7rOw4Sqm09V1

echo "
If you need to run this installation more than once, and generated passwords have changed,
be sure to remove and recreate the /postgresql_data/* dirs.
"

docker compose -f docker-compose-services-dev.yaml -p upstage-services-dev down --remove-orphans
#docker compose rm -f
docker compose -f docker-compose-services-dev.yaml -p upstage-services-dev up -d
sleep 5
docker compose ps
