#!/bin/bash
# This runs on the physical svc server by Let's Encrypt, and goes here:
# /etc/letsencrypt/renewal-hooks/deploy/mosquitto_renewal.sh

# Grab the id of the mosquitto user in the mosquitto container.
the_id=`docker exec -it -u mosquitto mosquitto_container "id" | grep -oP 'uid=\K\d+'`
the_gid=`docker exec -it -u mosquitto mosquitto_container "id" | grep -oP 'gid=\K\d+'`

# Update certs files mounted inside the container.
cp /etc/letsencrypt/live/*/* /mosquitto_files/etc/mosquitto/ca_certificates/ && chown ${the_id}:${the_gid} /mosquitto_files/etc/mosquitto/ca_certificates/*

# Do a soft kill, so processes/containers do not have to be restarted.
docker exec mosquitto_container kill -HUP $(docker exec mosquitto_container pidof mosquitto)

