"""Add per-assignment exit animation settings to parent_stage

Exit type/speed move from the asset's description JSON (global per media)
to the stage<->asset assignment, so the same media can exit differently
on each stage. NULL means the default: instant "vanish" at 1000 ms.

The repo intentionally carries two parallel alembic heads (see
7f1a5c9e02ad); compose runs `upgrade heads`. This revision chains onto
the stages-side head c0ffee125847 so head count stays at two.

Revision ID: b1e7a2d94c03
Revises: c0ffee125847
Create Date: 2026-07-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1e7a2d94c03"
down_revision: Union[str, None] = "c0ffee125847"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("parent_stage", sa.Column("exit_animation", sa.String(), nullable=True))
    op.add_column("parent_stage", sa.Column("exit_speed", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("parent_stage", "exit_speed")
    op.drop_column("parent_stage", "exit_animation")
