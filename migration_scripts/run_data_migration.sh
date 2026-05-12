#!/bin/bash
sudo apt update
sudo apt install postgresql-client

export LANG=C.UTF-8
export LC_ALL=C.UTF-8

read -p "Enter PostgreSQL host: " DB_HOST
read -p "Enter PostgreSQL port (default 5432): " DB_PORT
DB_PORT=${DB_PORT:-5432}
read -p "Enter PostgreSQL username: " DB_USER
read -s -p "Enter PostgreSQL password: " DB_PASSWORD
echo
read -p "Enter path to SQL backup file: " SQL_FILE

if [ ! -f "$SQL_FILE" ]; then
  echo "SQL file does not exist: $SQL_FILE"
  exit 1
fi

sed -i 's/OWNER TO upstage/OWNER TO postgres/g' $SQL_FILE 

export PGPASSWORD="$DB_PASSWORD"

echo "Creating database $DB_NAME if not exists..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'original_upstage'" | grep -q 1 || \
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"original_upstage\""

echo "Restoring database from $SQL_FILE..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d original_upstage -f  $SQL_FILE

echo "Done restoring database: $DB_NAME"

unset PGPASSWORD



set -a

# No PYTHONPATH manipulation: `upstage_backend` is editable-installed in
# the container venv (see app_containers/docker-compose.yaml
# `x-common-build` runtime stage), and `cd /usr/app` puts CWD on
# sys.path[0] for `python -m`, which makes `migration_scripts/` (a
# top-level dir COPYed into /usr/app at build time, with its own
# __init__.py) resolve as a package. The previous on-host
# `export PYTHONPATH=$(pwd)/src` was a no-op anyway — nothing on the
# host side of this script imports from upstage_backend.
container=`docker ps | grep upstage_backend| awk '{print $1}'`

docker cp  $SQL_FILE $container:/usr/app/

docker exec -it $container sh -c '
  cd /usr/app
  python3 -m migration_scripts.db_data_migration
'
