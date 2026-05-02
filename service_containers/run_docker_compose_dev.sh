#!/bin/bash

echo "This script may require root privileges."

set -a

SUFFIX=dev
DOCKERFILE=docker-compose-services.yaml
SERVICES=upstage-services-${SUFFIX}

HARDCODED_HOSTNAME=${SUFFIX}.upstage.live
PG_DATA_DIR=/postgres_data_${SUFFIX}
MQ_DATA_DIR=/mosquitto_files_${SUFFIX}

# Set this in your environment.
: "${POSTGRES_PASSWORD_DEV:?POSTGRES_PASSWORD_DEV is not set or is empty}" || exit 1

POSTGRES_PASSWORD=$POSTGRES_PASSWORD_DEV

if [ ! -d "${MQ_DATA_DIR}" ]; then
    sudo mkdir -p ${MQ_DATA_DIR}/etc/mosquitto/ca_certificates && \
        sudo mkdir -p ${MQ_DATA_DIR}/var/lib/mosquitto && \
        sudo cp -r ./deployment_config/etc_mosquitto/* ${MQ_DATA_DIR}/etc/mosquitto && \
        sudo chmod 700  ${MQ_DATA_DIR}/ca_certificates &&
        sudo chown -R 1883:1883 ${MQ_DATA_DIR}
    echo "Change the performance and admin passwords in this file: ${MQ_DATA_DIR}/etc/mosquitto/pw.backup"
    # We update mosquitto certs in a Let's Encrypt renenwal hook
    # script on the host server itself.
    #echo '0 0 * * * "cp /etc/letsencrypt/live/*/* /etc/mosquitto/ca_certificates/ && chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*"' > /tmp/mqttcron
    #crontab /tmp/mqttcron
    #rm -rf /tmp/mqttcron
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

docker network create upstage-network-${SUFFIX}

docker compose -f ${DOCKERFILE} -p ${SERVICES} down --remove-orphans
#docker compose rm -f
docker compose -f ${DOCKERFILE} -p ${SERVICES} up -d
docker compose -f ${DOCKERFILE} -p ${SERVICES} ps
