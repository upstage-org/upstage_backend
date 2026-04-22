#!/usr/bin/env bash
# Install nginx + certbot, minimal vhosts, obtain certificates for all three roles.
# Must run before service containers (mosquitto mounts /etc/letsencrypt).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
require_state_domains
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

export DEBIAN_FRONTEND=noninteractive
apt-get -y update
apt-get -y install nginx certbot python3-certbot-nginx

ufw status || true
ufw delete allow 'Nginx HTTP' 2>/dev/null || true
ufw allow 80/tcp
ufw allow 443/tcp
ufw status || true

mkdir -p /etc/nginx/ssl
if [[ ! -f /etc/nginx/ssl/dhparam.pem ]]; then
  openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
fi

rm -f /etc/nginx/sites-enabled/default
cat >/etc/nginx/sites-available/upstage-certbot-stub.conf <<EOF
# Temporary HTTP vhosts for Let's Encrypt (replaced in phase 51).
server {
    listen 80;
    listen [::]:80;
    server_name ${SVC_DOMAIN};
    location / { return 200 'ok'; add_header Content-Type text/plain; }
}
server {
    listen 80;
    listen [::]:80;
    server_name ${APP_DOMAIN};
    location / { return 200 'ok'; add_header Content-Type text/plain; }
}
server {
    listen 80;
    listen [::]:80;
    server_name ${STREAMING_DOMAIN} auth.${STREAMING_DOMAIN};
    location / { return 200 'ok'; add_header Content-Type text/plain; }
}
EOF
ln -sf /etc/nginx/sites-available/upstage-certbot-stub.conf /etc/nginx/sites-enabled/upstage-certbot-stub.conf
> /var/www/html/index.nginx-debian.html || true
nginx -t
systemctl reload nginx
systemctl enable nginx

# Separate certificates per hostname path expected by nginx templates under live/<domain>/
certbot --nginx -d "$SVC_DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect
certbot --nginx -d "$APP_DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect
certbot --nginx -d "$STREAMING_DOMAIN" -d "auth.${STREAMING_DOMAIN}" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect

echo "Certificates obtained. Full nginx config is applied in phase 51 after secrets and app tree."
