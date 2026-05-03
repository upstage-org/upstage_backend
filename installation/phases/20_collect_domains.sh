#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
STATE="$(state_file)"

if [[ -f "$STATE" ]] && [[ "${UPSTAGE_OVERWRITE_STATE:-}" != "1" ]]; then
  echo "Using existing $STATE (set UPSTAGE_OVERWRITE_STATE=1 to re-prompt)."
  # shellcheck disable=SC1090
  set -a
  source "$STATE"
  set +a
else
  read -r -p "App (public) hostname, e.g. app.example.org: " APP_DOMAIN
  read -r -p "Service hostname (Postgres/MQTT), e.g. svc.example.org: " SVC_DOMAIN
  read -r -p "Streaming/Jitsi hostname, e.g. streaming.example.org: " STREAMING_DOMAIN
  read -r -p "Let's Encrypt email (agreement + expiry notices): " CERTBOT_EMAIL
  read -r -p "Compose profile prod or dev [prod]: " UPSTAGE_COMPOSE_PROFILE
  UPSTAGE_COMPOSE_PROFILE=${UPSTAGE_COMPOSE_PROFILE:-prod}
fi

{
  echo "APP_DOMAIN=$APP_DOMAIN"
  echo "SVC_DOMAIN=$SVC_DOMAIN"
  echo "STREAMING_DOMAIN=$STREAMING_DOMAIN"
  echo "CERTBOT_EMAIL=$CERTBOT_EMAIL"
  echo "UPSTAGE_COMPOSE_PROFILE=$UPSTAGE_COMPOSE_PROFILE"
} >"$STATE"
chmod 600 "$STATE"

echo "Wrote $STATE"
hostnamectl set-hostname "${APP_DOMAIN%%.*}" 2>/dev/null || hostnamectl set-hostname "$APP_DOMAIN" || true
