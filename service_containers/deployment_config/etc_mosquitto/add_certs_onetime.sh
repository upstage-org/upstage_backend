#!/bin/sh
#
cp -L /etc/letsencrypt/live/${HARDCODED_HOSTNAME}/* /etc/mosquitto/ca_certificates/
chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*

