#!/bin/bash

# This file is generated. Do not change the generated copy. It will be
# overwritten.

set -a

export POSTGRES_PASSWORD=ejpqKHjYIln1
export MONGO_INITDB_ROOT_PASSWORD=bDUuq2i7Hgny

echo "
If you need to run this installation more than once, and generated passwords have changed,
be sure to remove and recreate the /postgresql_data/* dirs.
"

docker compose -f ./docker-compose-prod.yaml -p upstage-services-prod down
#docker compose rm -f
docker compose -f ./docker-compose-prod.yaml -p upstage-services-prod up -d
sleep 5
docker compose -f ./docker-compose-prod.yaml -p upstage-services-prod ps
