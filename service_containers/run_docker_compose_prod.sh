#!/bin/bash

# This file is generated. Do not change the generated copy. It will be
# overwritten.

set -a

# Set this in your environment.
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set or is empty}" || exit 1

echo "
If you need to run this installation more than once, and generated passwords have changed,
be sure to remove and recreate the /postgresql_data/* dirs.
"

docker compose -f ./docker-compose-services-prod.yaml -p upstage-services-prod down
#docker compose rm -f
docker compose -f ./docker-compose-services-prod.yaml -p upstage-services-prod up --build -d
docker compose -f ./docker-compose-services-prod.yaml -p upstage-services-prod ps
