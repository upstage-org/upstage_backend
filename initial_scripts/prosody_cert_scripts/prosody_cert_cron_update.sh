#!/bin/bash
#
dirpath=`echo /etc/letsencrypt/live/*/fullchain.pem`
dpath="$(dirname $dirpath)"
IFS='/' read -ra parts <<< "$dpath"
DOMAIN=${parts[4]}

#cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /var/lib/prosody/${DOMAIN}.crt
#cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /var/lib/prosody/${DOMAIN}.key
#cp /etc/letsencrypt/live/auth.${DOMAIN}/fullchain.pem /var/lib/prosody/auth.${DOMAIN}.crt
#cp /etc/letsencrypt/live/auth.${DOMAIN}/privkey.pem /var/lib/prosody/auth.${DOMAIN}.key

#chown prosody:prosody /etc/prosody/certs/* /var/lib/prosody/*

