#!/bin/sh
#
cp -L /etc/letsencrypt/live/dev.upstage.live/* /etc/mosquitto/ca_certificates/
chown mosquitto:mosquitto /etc/mosquitto/ca_certificates/*

