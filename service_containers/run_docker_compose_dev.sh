#!/bin/bash

echo "This script may require root privileges."

DOCKERFILE=docker-compose-services.yaml
SERVICES=upstage-services-dev

set -a

SUFFIX=dev
PG_DATA_DIR=/postgres_data_${SUFFIX}
MQ_DATA_DIR=/mosquitto_files_${SUFFIX}

# Set this in your environment.
: "${POSTGRES_PASSWORD_DEV:?POSTGRES_PASSWORD_DEV is not set or is empty}" || exit 1

POSTGRES_PASSWORD=$POSTGRES_PASSWORD_DEV

if [ ! -d "${MQ_DATA_DIR}" ]; then
    sudo mkdir -p ${MQ_DATA_DIR}/etc/mosquitto && \
        sudo mkdir -p ${MQ_DATA_DIR}/var/lib/mosquitto && \
        sudo cp -r ./deployment_config/etc_mosquitto/* ${MQ_DATA_DIR}/etc/mosquitto && \
        sudo chown -R 1883:1883 ${MQ_DATA_DIR}
    echo "Change the performance and admin passwords in this file: ${MQ_DATA_DIR}/etc/mosquitto/pw.backup"
    exit 0
else
    check_mqtt_pw=`grep performance ${MQ_DATA_DIR}/etc/mosquitto/pw.backup | grep performance | awk -F: '{print $2}'`
    if [ ${check_mqtt_pw} == 'changeme' ]; then
        echo "Change the performance and admin passwords in this file: ${MQ_DATA_DIR}/etc/mosquitto/pw.backup"
        exit 1
    fi
    check_mqtt_pw=`grep admin ${MQ_DATA_DIR}/etc/mosquitto/pw.backup | grep admin | awk -F: '{print $2}'`
    if [ ${check_mqtt_pw} == 'changeme' ]; then
        echo "Change the performance and admin passwords in this file: ${MQ_DATA_DIR}/etc/mosquitto/pw.backup"
        exit 1
    fi
fi

sudo chown -R 1883:1883 ${MQ_DATA_DIR}

if [ ! -d "${PG_DATA_DIR}" ]; then
    sudo mkdir -p ${PG_DATA_DIR}
    docker logs 
fi
sudo chown -R 999:999 ${PG_DATA_DIR}

docker compose -f ${DOCKERFILE} -p ${SERVICES} down --remove-orphans
#docker compose rm -f
docker compose -f ${DOCKERFILE} -p ${SERVICES} up -d
docker compose -f ${DOCKERFILE} -p ${SERVICES} ps
