#!/bin/bash

set -a

cd /streaming_files/jitsi-docker-jitsi-meet*
source /streaming_files/config/envfile 

# This is recreated by the docker config mount
rm -rf /streaming_config/jitsi-meet-cfg/web/keys

docker compose down
docker compose rm -f
docker compose up -d
