"""Consolidated baseline: full schema + install seeds.

Replaces the 41 hand-written revisions (two heads: a7f3c9e18b42 and
e3a9c7d51f20) that previously lived in per-module db_migrations/ dirs.
The schema is the exact pg_dump --schema-only of the fully-migrated dev
database (2026-07-26), stored in the sibling baseline001_schema.sql.
The seeds replicate the data the old migrations inserted on a fresh
install: default super admin (eb504467a5d7 — email updated to the
canonical support@upstage.live), default asset types (0baf970d7eb2),
default system configuration (e5f8bc8043a5) and email signature
(f6e7b37dc826). All seeds are insert-if-missing, so re-running against
an existing database is a no-op.

Databases created before this consolidation cannot downgrade past this
revision; restore from a pre-consolidation dump instead.

Revision ID: baseline001
Revises:
Create Date: 2026-07-26

"""

import json
from datetime import datetime
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Boolean, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import column, table

from upstage_backend.global_config.helpers.fernet_crypto import encrypt
from upstage_backend.users.db_models.user import SUPER_ADMIN

# revision identifiers, used by Alembic.
revision: str = "baseline001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA_SQL_PATH = Path(__file__).with_name("baseline001_schema.sql")

user_table = table(
    "upstage_user",
    column("id", Integer),
    column("username", Text),
    column("email", Text),
    column("password", Text),
    column("role", Integer),
    column("active", Boolean),
    column("created_on", TIMESTAMP(timezone=True)),
    column("last_login", TIMESTAMP(timezone=True)),
    column("bin_name", Text),
    column("can_send_email", Boolean),
)

asset_type_table = table("asset_type", column("name", String), column("file_location", String))

config_table = table(
    "config",
    column("name", String),
    column("value", Text),
)

default_asset_types = [
    "video",
    "backdrop",
    "audio",
    "curtain",
    "prop",
    "avatar",
]

config_defaults = {
    "TERMS_OF_SERVICE": "https://upstage.org.nz/?page_id=9622",
    "MANUAL": "https://docs.upstage.live/",
    "EMAIL_SUBJECT_PREFIX": "[UpStage Live]",
    "ENABLE_DONATE": json.dumps(False),
    "FOYER_TITLE": "UpStage: the cyberformance platform",
    "FOYER_DESCRIPTION": (
        '<h3 style="text-align: center;"><em>online venue for live performance and remote collaboration</em></h3>\n'
        '<p style="text-align: center;"><strong><a title="And now ... !" href="https://upstage.org.nz/?event=and-now" target="_blank" rel="noopener">'
        '<img src="https://upstage.org.nz/wp-content/uploads/2025/01/andnow2-1536x926.png" alt="And now ... !" width="600" height="362" /></a><!--And now ... " performances and presentation<br />'
        'Saturday 8th March 2025<br />18:00 CET (<a href="https://tinyurl.com/AndNow080325" target="_blank" rel="noopener">find your local time here</a>)'
        "</strong></p>\n"
        '<p style="text-align: center;">Visit <a title="UpStage.org.nz" href="http://upstage.org.nz" target="_blank" rel="noopener">upstage.org.nz</a> to find out more, sign up for news and walk throughs,<br />'
        "and support this independent open source artist-led project!</p>\n"
        "<p>--&gt;</p>--></strong></p>"
    ),
    "FOYER_MENU": (
        "UpStage User Manual (https://docs.upstage.live/)\n"
        "UpStage Website (https://upstage.org.nz/)\n"
        "Customise Foyer (/admin/configuration) (8,32)\n"
        "More\n"
        "> Contact (https://upstage.org.nz/?page_id=5)\n"
        "> FAQs (https://upstage.org.nz/?page_id=115)"
    ),
    "SHOW_REGISTRATION": json.dumps(True),
    "EMAIL_SIGNATURE": """
                Thank you,
                <br>
                <b style="color: #007011">The UpStage Team!</b>
                </p>
        """,
    "ADDING_EMAIL_SIGNATURE": json.dumps(True),
}


def upgrade() -> None:
    connection = op.get_bind()

    # Full schema, verbatim from pg_dump of the fully-migrated database.
    # exec_driver_sql bypasses text() so ':'-containing literals in the dump
    # are never mistaken for bind parameters; psycopg2 accepts the
    # multi-statement script.
    connection.exec_driver_sql(_SCHEMA_SQL_PATH.read_text())
    # The dump pins search_path to '' for its own statements; restore it so
    # the seed inserts (and any later revisions in this transaction) resolve
    # unqualified table names in public.
    connection.exec_driver_sql("SET search_path TO public")

    # --- default super admin ---
    exists = connection.execute(
        sa.select(user_table.c.username).where(user_table.c.username == "admin")
    ).fetchone()
    if exists is None:
        op.bulk_insert(
            user_table,
            [
                {
                    "username": "admin",
                    "email": "support@upstage.live",
                    "password": encrypt("Secret@123"),
                    "role": SUPER_ADMIN,
                    "active": True,
                    "created_on": datetime.now(),
                    "last_login": None,
                    "bin_name": "admin",
                    "can_send_email": True,
                }
            ],
        )

    # --- default asset types ---
    for asset_type in default_asset_types:
        result = connection.execute(
            sa.select(asset_type_table.c.name).where(asset_type_table.c.name == asset_type)
        ).fetchone()
        if not result:
            op.bulk_insert(asset_type_table, [{"name": asset_type, "file_location": asset_type}])

    # --- default system configuration ---
    for key, value in config_defaults.items():
        exists = connection.execute(
            sa.select(config_table.c.name).where(config_table.c.name == key)
        ).fetchone()
        if exists is None:
            connection.execute(config_table.insert().values(name=key, value=value))


def downgrade() -> None:
    raise NotImplementedError(
        "baseline001 is the consolidation floor; there is nothing to downgrade "
        "to. Restore from a pre-consolidation database dump instead."
    )
