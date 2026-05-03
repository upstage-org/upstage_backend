#!/bin/bash

for i in "${!SUFFIXES[@]}"; do
    suffix="${SUFFIXES[$i]}" \
    hostname="${HOSTNAMES[$i]}" \
    systemctl reload nginx && \
    cp /etc/letsencrypt/live/${hostname}/* ${MQ_DATA_DIR}/etc/mosquitto/ca_certificates/ && \
    chown 1883:1883 ${MQ_DATA_DIR}/etc/mosquitto/ca_certificates/* && \
    docker exec mosquitto_container_${suffix} kill -HUP 1"
done
