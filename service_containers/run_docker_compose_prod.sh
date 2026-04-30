#!/bin/bash

PG_DATA_DIR=/postgres_data
MQ_DATA_DIR=/mosquitto_files
DOCKERFILE=docker-compose-services-prod.yaml
SERVICES=upstage-services

set -a

# Set this in your environment.
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set or is empty}" || exit 1

check_mqtt_pw=`grep admin deployment_config/etc_mosquitto/pw.backup | grep performance | awk -F: '{print $2}'`
if [ ${check_mqtt_pw} == 'changeme' ]; then
    echo "Change the performance and admin passwords in this file: `pwd`/deployment_config/etc_mosquitto/pw.backup"
    exit 1
fi

check_mqtt_pw=`grep admin deployment_config/etc_mosquitto/pw.backup | grep admin | awk -F: '{print $2}'`
if [ ${check_mqtt_pw} == 'changeme' ]; then
    echo "Change the performance and admin passwords in this file: `pwd`/deployment_config/etc_mosquitto/pw.backup"
    exit 1
fi

if [ ! -d "${PG_DATA_DIR}" ]; then
    sudo mkdir -p ${PG_DATA_DIR} && sudo chown -R 999:999 ${PG_DATA_DIR}
fi

if [ ! -d "${MQ_DATA_DIR}" ]; then
    sudo mkdir -p ${MQ_DATA_DIR} && sudo chown -R 1883:1883 ${MQ_DATA_DIR}
    sudo mkdir -p ${MQ_DATA_DIR}/etc && sudo chown -R 1883:1883 ${MQ_DATA_DIR}/etc
    sudo cp -r deployment_config/etc_mosquitto/ ${MQ_DATA_DIR}/etc/mosquitto && sudo chown -R 1883:1883 ${MQ_DATA_DIR}/etc
fi

docker compose -f ${DOCKERFILE} -p ${SERVICES} down --remove-orphans
#docker compose rm -f
docker compose -f ${DOCKERFILE} -p ${SERVICES} up -d
docker compose -f ${DOCKERFILE} -p ${SERVICES} ps
