#!/usr/bin/env bash
# Run upstream generators only — same as service machine path in setup-your-domain.sh case 1.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/lib/common.sh"

require_root
BACKEND="$(resolve_backend_dir)"
[[ -n "$BACKEND" ]] || exit 1

cd "$BACKEND"
echo "Running initial_scripts/environments/generate_environments_script.sh (interactive)..."
bash initial_scripts/environments/generate_environments_script.sh

chmod +x ./scripts/generate_cipher_key.sh
echo "Running scripts/generate_cipher_key.sh ..."
bash ./scripts/generate_cipher_key.sh

GEN="$BACKEND/service_containers/run_docker_compose.sh"
if [[ ! -f "$GEN" ]]; then
  echo "Expected generated file missing: $GEN" >&2
  exit 1
fi
if ! grep -q '^export POSTGRES_PASSWORD=' "$GEN"; then
  echo "Generated $GEN does not contain expected export lines." >&2
  exit 1
fi
echo "Verified generated service run script contains DB password exports."
