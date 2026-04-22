#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
load_state
FRONTEND="$(resolve_frontend_dir)"
if [[ -z "$FRONTEND" ]]; then
  echo "Set UPSTAGE_FRONTEND_DIR or place prod_copy/upstage_frontend under the workspace root." >&2
  exit 1
fi

cd "$FRONTEND"
echo "Running frontend initial_scripts/generate_environments_script.sh (interactive)..."
bash initial_scripts/generate_environments_script.sh

profile="$(compose_profile)"
if [[ "$profile" == "dev" ]]; then
  bash run_front_end_dev.sh
else
  bash run_front_end_prod.sh
fi
