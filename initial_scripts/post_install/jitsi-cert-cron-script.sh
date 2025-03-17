#!/bin/bash

cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/fullchain.pem /var/lib/prosody/YOUR_DOMAIN_NAME.crt 
cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/fullchain.pem /var/lib/prosody/auth.YOUR_DOMAIN_NAME.crt
cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/privkey.pem /var/lib/prosody/YOUR_DOMAIN_NAME.key
cp /etc/letsencrypt/live/YOUR_DOMAIN_NAME/privkey.pem /var/lib/prosody/auth.YOUR_DOMAIN_NAME.key

