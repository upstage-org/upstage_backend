#!/bin/bash
# Run the password-update migration inside the running upstage_backend
# container. No PYTHONPATH manipulation: `upstage_backend` is editable-
# installed in the container venv (see app_containers/docker-compose.yaml
# `x-common-build` runtime stage), and `cd /usr/app` puts CWD on
# sys.path[0] for `python -m`, which makes `migration_scripts/` (a
# top-level dir COPYed into /usr/app at build time, with its own
# __init__.py) resolve as a package.
set -a

container=`docker ps | grep upstage_backend| awk '{print $1}'`

docker exec -it $container sh -c '
  cd /usr/app
  python3 -m migration_scripts.run_update_password
'
