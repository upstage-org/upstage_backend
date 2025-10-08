#!/bin/bash
set -a

container=`docker ps | grep upstage_backend| awk '{print $1}'`

docker exec -it $container sh -c '
  cd /usr/app
  PYTHONPATH=$(pwd)/src
  export PYTHONPATH
  python3 -m migration_scripts.run_update_password
'
