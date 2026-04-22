#!/usr/bin/env bash
# Jitsi / streaming role on the same host (from setup-your-domain.sh machine type 3).
# Run after TLS certs exist (phase 50) and before full nginx render (phase 51).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
require_state_domains
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

dname="$STREAMING_DOMAIN"
IFS='.' read -ra parts <<< "$dname"
if grep -q '^127.0.1.1' /etc/hosts; then
  sed -i "s/^127.0.1.1.*$/127.0.1.1 ${dname} auth.${dname} ${parts[0]} auth.${parts[0]}/" /etc/hosts
else
  echo "127.0.1.1 ${dname} auth.${dname} ${parts[0]} auth.${parts[0]}" >> /etc/hosts
fi

ufw allow 10000/udp comment 'jitsi-videobridge' || true

export DEBIAN_FRONTEND=noninteractive
apt-get -y update
apt-get -y install gnupg2

curl -fsSL https://download.jitsi.org/jitsi-key.gpg.key | gpg --dearmor -o /usr/share/keyrings/jitsi-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/jitsi-keyring.gpg] https://download.jitsi.org stable/" > /etc/apt/sources.list.d/jitsi-stable.list
apt-get -y update
apt-get -y upgrade

if [[ ! -f /etc/apt/sources.list.d/bookworm.list ]]; then
  echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list.d/bookworm.list
  apt-get update -y
fi
apt-get install -y openjdk-17-jre-headless

mkdir -p /etc/prosody/certs
cp "/etc/letsencrypt/live/${dname}/fullchain.pem" "/etc/prosody/certs/${dname}.crt"
cp "/etc/letsencrypt/live/${dname}/fullchain.pem" "/etc/prosody/certs/auth.${dname}.crt"
cp "/etc/letsencrypt/live/${dname}/privkey.pem" "/etc/prosody/certs/${dname}.key"
cp "/etc/letsencrypt/live/${dname}/privkey.pem" "/etc/prosody/certs/auth.${dname}.key"
chmod 640 /etc/prosody/certs/*key 2>/dev/null || true
chmod 644 /etc/prosody/certs/*crt 2>/dev/null || true

echo "
================================================================================
Install jitsi-meet (interactive). When prompted:
  - Hostname: ${dname} (not auth.${dname})
  - SSL: choose 'I want to use my own certificate'
  - Certificate: /etc/letsencrypt/live/${dname}/fullchain.pem
  - Private key:  /etc/letsencrypt/live/${dname}/privkey.pem
================================================================================
"
read -r -p "Press Enter to run: apt-get install jitsi-meet ..."

export DEBIAN_FRONTEND=dialog
apt-get install -y jitsi-meet

sed "s/YOUR_DOMAIN_NAME/${dname}/g" "$BACKEND/initial_scripts/post_install/jitsi-cert-cron-script.sh" >/root/jitsi-cert-cron-script.sh
chmod 755 /root/jitsi-cert-cron-script.sh
( crontab -l 2>/dev/null | grep -v jitsi-cert-cron-script; echo "0 1 * * * /root/jitsi-cert-cron-script.sh" ) | crontab -

chmod 640 /etc/prosody/certs/*key 2>/dev/null || true
chmod 644 /etc/prosody/certs/*crt 2>/dev/null || true
chown prosody:prosody /etc/prosody/certs/* 2>/dev/null || true

rm -f /etc/apt/sources.list.d/bookworm.list
apt-get update -y

echo "Jitsi phase done. Run phase 51 (nginx render) next so the UpStage streaming vhost matches this repo."
