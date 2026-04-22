#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
load_state
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

profile="$(compose_profile)"
bash "$HERE/lib/run_service_compose.sh" "$BACKEND" "$profile"

ufw allow 9002/tcp || true
echo "Service stack started. If Mosquitto fails, ensure certificates exist under /etc/letsencrypt."
