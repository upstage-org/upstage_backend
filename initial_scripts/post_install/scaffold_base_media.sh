#!/bin/bash
# Insert demo seed data (default users, demo stage, demo media, foyer copy,
# system configuration) into a freshly migrated upstage backend container.
#
# Run AFTER `upstage_db_migrate` has applied Alembic to heads (i.e. after
# `docker compose up`). Schema creation is Alembic's job; this script only
# inserts seed rows.
#
# Picks up whichever site-specific upstage_backend_<SITE> container is
# currently running and shells in to call the supported in-container
# wrapper script. No PYTHONPATH manipulation: the package is editable-
# installed in the venv, and `./scripts/run_scaffold_load.sh` activates
# that venv itself.

set -euo pipefail

container=$(docker ps --filter "name=upstage_backend_" --format '{{.Names}}' | head -n1)

if [[ -z "${container}" ]]; then
  echo "ERROR: no running container matching name=upstage_backend_*. Bring the stack up with docker compose first." >&2
  exit 1
fi

echo "Inserting scaffold seed data into ${container} ..."
docker exec -i "${container}" ./scripts/run_scaffold_load.sh
echo "Scaffold seed data load complete."
