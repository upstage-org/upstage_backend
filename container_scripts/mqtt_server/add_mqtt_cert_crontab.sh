#!/bin/sh
#
## One-time setup as root:
mkdir -p /etc/mosquitto/ca_certificates/
chmod 755 /etc/mosquitto/ca_certificates/
chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/

cp /etc/letsencrypt/live/*/* /etc/mosquitto/ca_certificates/
chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*

# crontab does not run in the mosquitto docker container.
# Instead, we update mosquitto certs in a Let's Encrypt renenwal hook 
# script on the server itself.
#echo '0 0 * * * "cp /etc/letsencrypt/live/*/* /etc/mosquitto/ca_certificates/ && chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*"' > /tmp/mqttcron
#crontab /tmp/mqttcron
#rm -rf /tmp/mqttcron

