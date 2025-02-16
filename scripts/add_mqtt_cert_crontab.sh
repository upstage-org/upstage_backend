#!/bin/bash
#
## One-time setup as root:
mkdir -p /etc/mosquitto/ca_certificates/
chmod 755 /etc/mosquitto/ca_certificates/
chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/

cp /etc/letsencrypt/live/*/* /etc/mosquitto/ca_certificates/
chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*

echo '0 0 * * * "cp /etc/letsencrypt/live/*/* /etc/mosquitto/ca_certificates/ && chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*"' > /tmp/mqttcron
crontab /tmp/mqttcron
rm -rf /tmp/mqttcron
