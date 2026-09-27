"""Every timestamp column becomes `timestamp with time zone`.

The schema mixed the two types (21 columns without a zone, 14 with), and
the application wrote naive `datetime.now()` into both. The naive values
are UTC wall-clock time - the containers and Postgres run in UTC, and the
column defaults say `now() AT TIME ZONE 'utc'` - so they are converted as
UTC. From here on the application only handles aware datetimes.

With the session time zone set to UTC, PostgreSQL 12+ does not rewrite the
table for `timestamp` -> `timestamptz`, but it does rebuild the indexes on
the converted column (measured on PostgreSQL 18: `events` kept its
relfilenode, `events_created` got a new one). Each ALTER holds an ACCESS
EXCLUSIVE lock for that long, so run this while no performance is live:
`events`, `connection_stats` and `receive_stats` are the tables that grow.
The short lock_timeout makes the migration fail (it can simply be re-run)
rather than queue behind a long transaction and block every request.

Revision ID: b9d2f4a6c8e0
Revises: a7c1e2d4f6b8
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9d2f4a6c8e0"
down_revision: Union[str, None] = "a7c1e2d4f6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UTC_NOW_NAIVE = "(now() AT TIME ZONE 'utc'::text)"

# (table, column, column default before this revision or None)
COLUMNS = [
    ("admin_one_time_totp_qr_url", "recorded_time", None),
    ("asset", "created_on", UTC_NOW_NAIVE),
    ("asset", "updated_on", UTC_NOW_NAIVE),
    ("asset_license", "created_on", UTC_NOW_NAIVE),
    ("asset_type", "created_on", UTC_NOW_NAIVE),
    ("asset_usage", "created_on", UTC_NOW_NAIVE),
    ("config", "created_on", UTC_NOW_NAIVE),
    ("connection_stats", "mqtt_timestamp", None),
    ("connection_stats", "created", None),
    ("events", "created", "CURRENT_TIMESTAMP"),
    ("jwt_no_list", "remove_after", UTC_NOW_NAIVE),
    ("media_tag", "created_on", UTC_NOW_NAIVE),
    ("performance_config", "created_on", None),
    ("performance_config", "expires_on", None),
    ("receive_stats", "mqtt_timestamp", None),
    ("receive_stats", "created", None),
    ("stage", "created_on", UTC_NOW_NAIVE),
    ("stage", "last_access", None),
    ("stage_statistics", "updated_on", "now()"),
    ("tag", "created_on", UTC_NOW_NAIVE),
    ("user_session", "recorded_time", UTC_NOW_NAIVE),
]


def _session_settings() -> None:
    op.execute("SET LOCAL timezone = 'UTC'")
    op.execute("SET LOCAL lock_timeout = '10s'")


def upgrade() -> None:
    _session_settings()
    for table, column, default in COLUMNS:
        op.execute(
            f'ALTER TABLE public."{table}" ALTER COLUMN "{column}" TYPE timestamp with time zone'
        )
        if default == UTC_NOW_NAIVE:
            op.execute(f'ALTER TABLE public."{table}" ALTER COLUMN "{column}" SET DEFAULT now()')


def downgrade() -> None:
    _session_settings()
    for table, column, default in reversed(COLUMNS):
        op.execute(
            f'ALTER TABLE public."{table}" ALTER COLUMN "{column}" TYPE timestamp without time zone'
        )
        if default == UTC_NOW_NAIVE:
            op.execute(
                f'ALTER TABLE public."{table}" ALTER COLUMN "{column}" SET DEFAULT {UTC_NOW_NAIVE}'
            )
