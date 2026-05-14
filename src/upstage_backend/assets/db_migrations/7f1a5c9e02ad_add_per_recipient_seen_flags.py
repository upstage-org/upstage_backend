"""Add per-recipient seen flags to asset_usage

Revision ID: 7f1a5c9e02ad
Revises: b2c4d6e81023
Create Date: 2026-05-13 19:00:00.000000

Adds `owner_seen` and `requester_seen` boolean columns to `asset_usage` to
support the three-way notification bell:

  * pending strict request  -> owner sees until owner_seen=True
  * acknowledgement (FYI)   -> owner sees until owner_seen=True
  * approval-granted result -> requester sees until requester_seen=True

Existing rows are backfilled to `True` for both flags so nothing already
on disk pops up in anyone's bell after upgrade. The legacy `seen`
column is removed by the follow-up migration `c1a4d3f7e29b`.

Chained off `b2c4d6e81023` (the most recent leaf migration); the
parallel `a09bc4e8f1d0` head remains unaffected. `alembic upgrade
heads` continues to apply everything.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f1a5c9e02ad"
down_revision: Union[str, None] = "b2c4d6e81023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Two steps per column: add nullable, backfill existing rows, then
    # tighten to NOT NULL. Adding NOT NULL + default in one go on a
    # large table can hold a long lock on Postgres; this pattern is
    # safe even when the table has many rows.
    op.add_column(
        "asset_usage",
        sa.Column("owner_seen", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "asset_usage",
        sa.Column("requester_seen", sa.Boolean(), nullable=True),
    )

    # Backfill: every pre-existing row predates the new bell semantics,
    # so neither side should be re-prompted. Setting both to TRUE means
    # no historical row will appear in get_notifications after upgrade.
    op.execute(
        "UPDATE asset_usage SET owner_seen = TRUE, requester_seen = TRUE "
        "WHERE owner_seen IS NULL OR requester_seen IS NULL"
    )

    op.alter_column(
        "asset_usage",
        "owner_seen",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("FALSE"),
    )
    op.alter_column(
        "asset_usage",
        "requester_seen",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("FALSE"),
    )


def downgrade() -> None:
    op.drop_column("asset_usage", "requester_seen")
    op.drop_column("asset_usage", "owner_seen")
