#!/bin/bash

find /app_code/uploads -maxdepth 1 -not -path /app_code/uploads -exec rm -rf {} +

unzip /root/databases/assets.zip -d /app_code/uploads/ && mv /app_code/uploads/assets/*  /app_code/uploads/  && rm -rf /app_code/uploads/assets

USER_ID=$(docker exec -it upstage_container id -u | tr -d '\r')
GROUP_ID=$(docker exec -it upstage_container id -g | tr -d '\r')

# Check if IDs were retrieved successfully
if [ -z "$USER_ID" ] || [ -z "$GROUP_ID" ]; then
    echo "Error: Could not retrieve USER_ID or GROUP_ID from the container."
    exit 1
fi

# Change ownership and permissions for directories using dynamic IDs
sudo chown -R ${USER_ID}:${GROUP_ID} /app_code/uploads
sudo chmod -R 775 /app_code/uploads