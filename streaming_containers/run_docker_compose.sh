#!/bin/bash

set -a

cd /streaming_files/jitsi-docker-jitsi-meet*
source /streaming_files/config/envfile 

# TO DO: Fix volume in docker-compose for lets encrypt and repo

docker compose down
docker compose up -d
