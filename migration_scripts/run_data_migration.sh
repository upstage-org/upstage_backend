#!/bin/bash

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

export PGPASSWORD="$DB_PASSWORD"

echo "Creating database $DB_NAME if not exists..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'original_upstage'" | grep -q 1 || \
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"original_upstage\""

echo "Restoring database from $SQL_FILE..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d original_upstage -f "upstage.sql"

echo "Done restoring database: $DB_NAME"

unset PGPASSWORD



set -a


export PYTHONPATH=$(pwd)/src


container=`docker ps | grep upstage_container| awk '{print $1}'`

docker cp $DB_NAME $container:/usr/app/

docker exec -it $container sh -c '
  cd /usr/app
  PYTHONPATH=$(pwd)/src
  export PYTHONPATH
  python3 -m migration_scripts.db_data_migration
'