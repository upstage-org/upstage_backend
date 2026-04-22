#!/usr/bin/env bash
# Copy app tree to /app_code, sync mosquitto files (after pw.txt exists), apply HOSTNAME sed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
require_state_domains
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

cd "$BACKEND"

# Mosquitto + renewal (same as setup-your-domain.sh case 1)
cp ./container_scripts/mqtt_server/mosquitto_renewal.sh /etc/letsencrypt/renewal-hooks/deploy/mosquitto_renewal.sh
cp ./container_scripts/mqtt_server/mosquitto.conf /mosquitto_files/etc/mosquitto/mosquitto.conf
cp ./container_scripts/mqtt_server/pw.txt /mosquitto_files/etc/mosquitto/pw.txt
cp ./container_scripts/mqtt_server/pw.txt /mosquitto_files/etc/mosquitto/pw.backup
cp ./container_scripts/mqtt_server/local_mosquitto.conf /mosquitto_files/etc/mosquitto/conf.d/local_mosquitto.conf
cp ./container_scripts/mqtt_server/add_mqtt_cert_crontab.sh /mosquitto_files/etc/mosquitto/cron/add_mqtt_cert_crontab.sh

# App tree (case 2)
cp -r ./src /app_code
cp -r ./alembic /app_code
cp -r ./scripts /app_code
cp -r ./dashboard/demo /app_code
cp -r ./requirements.txt /app_code
[[ -f ./pyproject.toml ]] && cp -r ./pyproject.toml /app_code
[[ -d ./migration_scripts ]] && cp -r ./migration_scripts /app_code
chmod -R 777 /app_code/alembic
chmod -R 777 /app_code/uploads

output_file="/app_code/src/global_config/load_env.py"
chmod 755 "$output_file"
sed -i "s/{APP_HOST}/${APP_DOMAIN}/g" "$output_file"

echo "Synced load_env.py and app tree; HOSTNAME line uses APP_DOMAIN $APP_DOMAIN"

# Same-host: no SCP — load_env already generated in repo and copied with ./src
echo "If you use shared email UFW rules from multi-machine docs, on a single host use docker-firewall-config.md + phase 75 instead of run_these_ufw_commands_on_svc_machine.sh."
