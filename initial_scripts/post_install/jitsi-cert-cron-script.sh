#!/bin/bash

cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/fullchain.pem /etc/prosody/certs/YOUR_DOMAIN_NAME.crt
cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/fullchain.pem /etc/prosody/certs/auth.YOUR_DOMAIN_NAME.crt
cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/privkey.pem /etc/prosody/certs/YOUR_DOMAIN_NAME.key
cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/privkey.pem /etc/prosody/certs/auth.YOUR_DOMAIN_NAME.key

chmod 640 /etc/prosody/certs/*key
chmod 644 /etc/prosody/certs/*crt
chown prosody:prosody /etc/prosody/certs/*

