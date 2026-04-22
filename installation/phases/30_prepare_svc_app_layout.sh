#!/usr/bin/env bash
# Create data directories (no secrets yet). Secrets and mosquitto pw files are applied after phase 40.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
require_state_domains
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || { echo "Backend dir not found"; exit 1; }

mkdir -p /postgresql_data/var /postgresql_data/data
mkdir -p /mongodb_data_volume
mkdir -p /mosquitto_files/etc/mosquitto/conf.d
mkdir -p /mosquitto_files/etc/mosquitto/cron
mkdir -p /mosquitto_files/var/lib/mosquitto
mkdir -p /frontend_code
mkdir -p /app_code/demo /app_code/uploads

echo "Data directories created."
