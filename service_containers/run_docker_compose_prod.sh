#!/bin/bash

echo "This script may require root privileges."

set -a

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# These have to be set in both dev and prod scripts for SSL support and cert update deploy hook.
#
# Check/change the values of these variables before running.
# 

BASE_SITE=upstage.live
SITES=("dev","prod")
HOSTNAMES=("dev.${BASE_SITE}","${BASE_SITE}")

# Set this empty to turn SSL off for Mosquitto.
# NOTE: Uncomment the MQTT port section in the docker-compose-services.yaml file
# only if you're running locally.
#SSL=mqtt.${BASE_SITE}
SSL=

SITE=prod
DOCKERFILE=docker-compose-services.yaml
SERVICES=upstage-services-${SITE}

if [[ -z $SSL ]]; then
    MOSQUITTO_EXPOSED_WS_PORT=2053 # for running locally
else
    MOSQUITTO_EXPOSED_WS_PORT=443 # scoped by domain name in nginx
fi

HARDCODED_HOSTNAME=upstage.live
PG_DATA_DIR=/postgres_data_${SITE}
MQ_DATA_DIR=/mosquitto_files_${SITE}

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Set this in your environment: export POSTGRES_PASSWORD_DEV=NNNNN for example.
var="POSTGRES_PASSWORD_${SITE^^}"
POSTGRES_PASSWORD="${!var}"
: "${POSTGRES_PASSWORD:?$var is not set or is empty}" || exit 1

if [ ! -d "${MQ_DATA_DIR}" ]; then
    echo "First time MQTT setup..."
    sudo mkdir -p ${MQ_DATA_DIR}/etc/mosquitto/http && \
        sudo mkdir -p ${MQ_DATA_DIR}/var/lib/mosquitto && \
        sudo cp -r ./deployment_config/etc_mosquitto/* ${MQ_DATA_DIR}/etc/mosquitto && \
        sudo chown -R 1883:1883 ${MQ_DATA_DIR}
    echo "Change the performance and admin passwords in this file: ${MQ_DATA_DIR}/etc/mosquitto/pw.backup"

    # SSL for mqtt is handled by nginx, and an mqtt.* domain name.
    # We'll just install the letsencrypt deploy hook to reload nginx when certs are updated.
	sudo cat << EOF > /root/letsencrypt_deploy_hook.sh
$(cat deployment_config/on_server/letsencrypt_deploy_hook.sh.template)
EOF
    sudo chmod 755 /root/letsencrypt_deploy_hook.sh
    sudo certbot certonly \
     --webroot \
     --webroot-path /var/www/html \
     -d ${HARDCODED_HOSTNAME} \
     --deploy-hook /root/letsencrypt_deploy_hook.sh

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
