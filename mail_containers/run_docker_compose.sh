#!/bin/bash

set -a

docker compose up -d
sleep 5
docker compose ps
