"""upload_limit: backfill NULL to the 1 MiB default and add a server default.

Until 2026-09-11 a NULL upstage_user.upload_limit meant "no per-user cap":
the server let such a player push anything up to the 500 MiB server-wide
maximum and whoami reported 500 MB, while Player Management showed "0 B".
NULL only ever arose by accident (rows inserted outside the ORM: the
migration-seeded admin, batch-created users, accounts predating the
column), and admins are exempt from the per-user cap by role now, so the
policy (users.services.upload_limit) reads NULL as the 1 MiB default and
this revision makes the stored data say the same thing.

Revision ID: c3d5e7f9a1b2
Revises: baseline001
Create Date: 2026-09-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d5e7f9a1b2"
down_revision: Union[str, None] = "baseline001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_PLAYER_UPLOAD_LIMIT = 1024 * 1024


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE upstage_user SET upload_limit = :limit WHERE upload_limit IS NULL"
        ).bindparams(limit=DEFAULT_PLAYER_UPLOAD_LIMIT)
    )
    # Rows inserted without the ORM (raw SQL, bulk loads) get the default too.
    op.alter_column(
        "upstage_user",
        "upload_limit",
        existing_type=sa.Integer(),
        server_default=sa.text(str(DEFAULT_PLAYER_UPLOAD_LIMIT)),
        existing_nullable=True,
    )


def downgrade() -> None:
    # The backfilled rows cannot be told apart from ones that were 1 MiB
    # already, so only the server default is undone.
    op.alter_column(
        "upstage_user",
        "upload_limit",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=True,
    )
