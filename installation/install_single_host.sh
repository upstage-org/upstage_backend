#!/usr/bin/env bash
# Single-host orchestrator for UpStage (Debian). Run as root from the installation directory.
# Does not modify files outside this directory except system paths (/etc, /app_code, Docker, etc.).
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$INSTALL_DIR/lib/common.sh"

usage() {
  cat <<EOF
Usage: $0 [--list] | [--phase <name>] | [--all]

  --list          List phase names and exit
  --phase <name>  Run one phase (see phases/*.sh without .sh)
  --all           Run full install in order (default)

Phase order for --all:
  10_os 20_collect_domains 30_prepare_svc_app_layout 50_certificates
  40_generate_secrets 45_sync_load_env 80_streaming_jitsi 51_nginx_render_full
  60_compose_svc 75_docker_firewall 70_compose_app 90_frontend

Environment:
  UPSTAGE_BACKEND_DIR   Path to upstage_backend checkout (default: ../prod_copy/upstage_backend)
  UPSTAGE_FRONTEND_DIR  Path to upstage_frontend checkout
  UPSTAGE_OVERWRITE_STATE=1  Re-prompt domain questions in phase 20

EOF
}

list_phases() {
  echo "Available phases:"
  for f in "$INSTALL_DIR"/phases/*.sh; do
    basename "$f" .sh
  done
}

run_phase() {
  local name="$1"
  local script="$INSTALL_DIR/phases/${name}.sh"
  if [[ ! -f "$script" ]]; then
    echo "Unknown phase: $name (expected $script)" >&2
    exit 1
  fi
  echo "===== Phase: $name ====="
  bash "$script"
}

main() {
  local mode="all"
  local single=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --list) list_phases; exit 0 ;;
      --phase) single="$2"; mode="single"; shift 2 ;;
      --all) mode="all"; shift ;;
      -h|--help) usage; exit 0 ;;
      *) usage; exit 1 ;;
    esac
  done

  if [[ "$mode" == "single" ]]; then
    run_phase "$single"
    exit 0
  fi

  local order=(
    10_os
    20_collect_domains
    30_prepare_svc_app_layout
    50_certificates
    40_generate_secrets
    45_sync_load_env
    80_streaming_jitsi
    51_nginx_render_full
    60_compose_svc
    75_docker_firewall
    70_compose_app
    90_frontend
  )

  for p in "${order[@]}"; do
    run_phase "$p"
  done
  echo "All phases completed."
}

main "$@"
