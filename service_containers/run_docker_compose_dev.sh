#!/bin/bash

PG_DATA_DIR=/postgres_data_dev
MQ_DATA_DIR=/mosquitto_files_dev
DOCKERFILE=docker-compose-services-dev.yaml
SERVICES=upstage-services-dev

set -a

# Set this in your environment.
: "${POSTGRES_PASSWORD_DEV:?POSTGRES_PASSWORD_DEV is not set or is empty}" || exit 1

POSTGRES_PASSWORD=$POSTGRES_PASSWORD_DEV

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
