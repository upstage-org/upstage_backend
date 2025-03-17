#!/bin/bash

set -a

cd /streaming_files/jitsi-docker-jitsi-meet*
source /streaming_files/config/envfile 

docker compose down
docker compose rm -f
docker compose up -d
