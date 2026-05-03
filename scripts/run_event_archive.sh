#!/bin/bash
set -e
cd /usr/app
VENV="${VIRTUAL_ENV:-/usr/app/.venv}"
export VIRTUAL_ENV="$VENV"
export PATH="${VENV}/bin:${PATH}"
export PYTHONPATH="/usr/app/src${PYTHONPATH:+:$PYTHONPATH}"
exec python -m scripts.run_event_archive
