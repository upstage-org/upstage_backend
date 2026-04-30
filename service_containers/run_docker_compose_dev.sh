#!/bin/bash

# This file is generated. Do not change the generated copy. It will be
# overwritten.

set -a

# Set this in your environment.
: "${POSTGRES_PASSWORD_DEV:?POSTGRES_PASSWORD_DEV is not set or is empty}" || exit 1

POSTGRES_PASSWORD=$POSTGRES_PASSWORD_DEV

echo "
If you need to run this installation more than once, and generated passwords have changed,
be sure to remove and recreate the /postgresql_data/* dirs.
"

docker compose -f docker-compose-services-dev.yaml -p upstage-services-dev down --remove-orphans
#docker compose rm -f
docker compose -f docker-compose-services-dev.yaml -p upstage-services-dev up -d
docker compose -f docker-compose-services-dev.yaml -p upstage-services-dev ps
