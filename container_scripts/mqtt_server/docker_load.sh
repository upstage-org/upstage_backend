#!/bin/bash
gunzip -f ./mqttserver_latest.tar.gz
docker load < ./mqttserver_latest.tar
docker run -p 1884:1883 -p 9002:9001 mqttserver:latest
