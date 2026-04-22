#!/usr/bin/env bash
# Replace stub with combined vhosts from backend templates.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
require_state_domains
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

export APP_DOMAIN SVC_DOMAIN STREAMING_DOMAIN
bash "$HERE/lib/render_nginx.sh" "$BACKEND" /etc/nginx/sites-available/upstage-single-host.conf

rm -f /etc/nginx/sites-enabled/upstage-certbot-stub.conf
ln -sf /etc/nginx/sites-available/upstage-single-host.conf /etc/nginx/sites-enabled/upstage-single-host.conf

nginx -t
systemctl reload nginx
echo "Full nginx configuration installed."
