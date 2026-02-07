# All migrations must live in the corresponding src/N/db_migrations folder.
# Configured in scripts/alembic.ini version_locations:
#   src/users/db_migrations
#   src/authentication/db_migrations
#   src/assets/db_migrations
#   src/stages/db_migrations
#   src/upstage_options/db_migrations
#   src/event_archive/db_migrations
#   src/performance_config/db_migrations
#   src/upstage_stats/db_migrations
#
# Run from project root with: alembic -c scripts/alembic.ini revision -m "Description" --version-path=src/<app>/db_migrations
#
# alembic revision -m "Create Tag Table"  --version-path=src/assets/db_migrations
# alembic revision -m "Create Stage Table"  --version-path=src/stages/db_migrations
# alembic revision -m "Create Event Table"  --version-path=src/event_archive/db_migrations
# alembic revision -m "Create Connection Stat Table"  --version-path=src/upstage_stats/db_migrations
# alembic revision -m "Create One Time OTP"  --version-path=src/users/db_migrations
# alembic revision -m "Add performance duration"  --version-path=src/performance_config/db_migrations