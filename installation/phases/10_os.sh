#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
BACKEND="$(resolve_backend_dir)"
if [[ -z "$BACKEND" ]]; then
  echo "Set UPSTAGE_BACKEND_DIR or place prod_copy/upstage_backend under the workspace root." >&2
  exit 1
fi

echo "Running initial_scripts/setup-os.sh from $BACKEND ..."
export DEBIAN_FRONTEND=noninteractive
cd "$BACKEND"
bash initial_scripts/setup-os.sh
