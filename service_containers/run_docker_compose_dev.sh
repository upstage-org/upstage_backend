#!/bin/bash

echo "This script may require root privileges."

set -a

# Set this to any value to turn ON SSL installation features.
SSL=

# These have to be set in both dev and prod scripts for SSL support and cert update deploy hook.
SITES=("dev","prod")
HOSTNAMES=("dev.upstage.live","upstage.live")

SITE=dev
DOCKERFILE=docker-compose-services.yaml
SERVICES=upstage-services-${SITE}
MOSQUITTO_EXPOSED_WS_PORT=2087    # CloudFlare-friendly port

HARDCODED_HOSTNAME=${SITE}.upstage.live
PG_DATA_DIR=/postgres_data_${SITE}
MQ_DATA_DIR=/mosquitto_files_${SITE}

# Set this in your environment: export POSTGRES_PASSWORD_DEV=NNNNN for example.
var="POSTGRES_PASSWORD_${SITE^^}"
POSTGRES_PASSWORD="${!var^^}"
: "${POSTGRES_PASSWORD:?$var is not set or is empty}" || exit 1

if [ ! -d "${MQ_DATA_DIR}" ]; then
    echo "First time MQTT setup..."
    sudo mkdir -p ${MQ_DATA_DIR}/etc/mosquitto/ca_certificates && \
        sudo mkdir -p ${MQ_DATA_DIR}/etc/mosquitto/http && \
        sudo mkdir -p ${MQ_DATA_DIR}/var/lib/mosquitto && \
        sudo cp -r ./deployment_config/etc_mosquitto/* ${MQ_DATA_DIR}/etc/mosquitto && \
        sudo chmod 700  ${MQ_DATA_DIR}/etc/mosquitto/ca_certificates &&
        sudo chown -R 1883:1883 ${MQ_DATA_DIR}
    echo "Change the performance and admin passwords in this file: ${MQ_DATA_DIR}/etc/mosquitto/pw.backup"

    if [[ ! -z $SSL ]]; then
        # We update mosquitto certs in a Let's Encrypt renenwal hook
        # script on the host server itself.
        sudo rm -f ${MQ_DATA_DIR}/etc/mosquitto/conf.d/local_mosquitto_nossl.conf
        sudo certbot certonly \
         --webroot \
         --webroot-path /var/www/html \
         -d ${HARDCODED_HOSTNAME} \
         --deploy-hook "./deployment_config/on_server/letsencrypt_deploy_hook.sh"
    else
        sudo rm -f ${MQ_DATA_DIR}/etc/mosquitto/conf.d/local_mosquitto_ssl.conf
    fi

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
    echo "First time Postgres setup..."
    sudo mkdir -p ${PG_DATA_DIR}
fi
sudo chown -R 999:999 ${PG_DATA_DIR}

docker network create upstage-network-${SITE}

docker compose -f ${DOCKERFILE} -p ${SERVICES} down --remove-orphans
#docker compose rm -f
docker compose -f ${DOCKERFILE} -p ${SERVICES} up -d
docker compose -f ${DOCKERFILE} -p ${SERVICES} ps

counter=0
firstrun_fail=`docker logs postgres_container_${SITE} 2>&1 | grep -i "initdb\|could not change permissions\|No such container"`
while [[ -n $firstrun_fail ]] && [ "$counter" -lt 3 ]
do
    echo "Restarting Postgres...${firstrun_fail}"
    sleep 3
    docker compose -f ${DOCKERFILE} -p ${SERVICES} down --remove-orphans postgres
    sudo chown -R 999:999 ${PG_DATA_DIR}
    docker compose -f ${DOCKERFILE} -p ${SERVICES} up -d postgres
    docker compose -f ${DOCKERFILE} -p ${SERVICES} ps
    counter=$((counter + 1))
    firstrun_fail=`docker logs postgres_container_${SITE} 2>&1 | grep -i "initdb\|could not change permissions\|No such container"`
done

counter=0
firstrun_fail=`docker logs mosquitto_container_${SITE} 2>&1 | grep -i "Permission denied\|could not change permissions\|No such container"`
while [[ -n $firstrun_fail ]] && [ "$counter" -lt 3 ]
do
    echo "Restarting Mosquitto...${firstrun_fail}"
    sleep 3
    docker compose -f ${DOCKERFILE} -p ${SERVICES} down --remove-orphans mosquitto
    sudo chown -R 1883:1883 ${MQ_DATA_DIR}
    docker compose -f ${DOCKERFILE} -p ${SERVICES} up -d mosquitto
    docker compose -f ${DOCKERFILE} -p ${SERVICES} ps
    counter=$((counter + 1))
    firstrun_fail=`docker logs mosquitto_container_${SITE} 2>&1 | grep -i "Permission denied\|could not change permissions\|No such container"`
done
