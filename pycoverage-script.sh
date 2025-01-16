export PGPASSWORD="postgres"
psql -h localhost -p 5432 -U postgres -c "DROP DATABASE IF EXISTS upstage_test;"
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE upstage_test;"
alembic upgrade head
coverage run -m pytest