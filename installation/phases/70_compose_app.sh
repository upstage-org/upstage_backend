#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
load_state
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

cd "$BACKEND/app_containers"
profile="$(compose_profile)"
if [[ "$profile" == "dev" ]]; then
  bash run_docker_compose_dev.sh
else
  bash run_docker_compose_prod.sh
fi
