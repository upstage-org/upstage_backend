#!/bin/bash
# In-container wrapper for the upstage_stats service. Activates the
# editable-installed venv and hands off to the `scripts.run_upstage_stats`
# module entry point.
#
# No PYTHONPATH manipulation: `upstage_backend` is `pip install -e .`-d
# into ${VIRTUAL_ENV} during the Docker build (see
# app_containers/docker-compose.yaml `x-common-build` runtime stage), and
# `cd /usr/app` puts CWD on sys.path[0] for `python -m`, which makes
# `scripts.run_upstage_stats` (and `scripts/__init__.py`) resolve.
set -e
cd /usr/app
VENV="${VIRTUAL_ENV:-/usr/app/.venv}"
export VIRTUAL_ENV="$VENV"
export PATH="${VENV}/bin:${PATH}"
exec python -m scripts.run_upstage_stats
