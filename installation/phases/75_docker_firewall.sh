#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

ensure_ufw_loopback_docker

cd "$BACKEND"
if [[ ! -f initial_scripts/setup-docker-ports.sh ]]; then
  echo "Missing setup-docker-ports.sh" >&2
  exit 1
fi
bash initial_scripts/setup-docker-ports.sh
