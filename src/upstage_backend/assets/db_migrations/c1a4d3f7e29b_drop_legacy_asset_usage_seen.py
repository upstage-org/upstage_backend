"""Drop legacy asset_usage.seen column

Revision ID: c1a4d3f7e29b
Revises: 7f1a5c9e02ad
Create Date: 2026-05-13 20:00:00.000000

The original single-bit `seen` flag is superseded by the per-recipient
`owner_seen` / `requester_seen` columns introduced in 7f1a5c9e02ad.
With every consumer (ORM model, services, GraphQL SDL, frontend
queries / fragments / TS types, docs, tests) updated to ignore it,
the column is now dead weight and can be dropped.

If we ever need to roll back past this migration AND need
`seen`-driven bell behaviour again, the downgrade recreates the
column. The downgrade backfills approved rows to `seen=TRUE` to mirror
the historical contract (approved => seen) that
StudioService.confirm_permission used to maintain.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1a4d3f7e29b"
down_revision: Union[str, None] = "7f1a5c9e02ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("asset_usage", "seen")


def downgrade() -> None:
    op.add_column(
        "asset_usage",
        sa.Column("seen", sa.Boolean(), nullable=True),
    )
    # Historical contract: confirm_permission set seen=True alongside
    # approved=True. Approximate that on the way back.
    op.execute("UPDATE asset_usage SET seen = approved WHERE seen IS NULL")
    op.alter_column(
        "asset_usage",
        "seen",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("FALSE"),
    )
