"""Create Stage Statistics Table

Revision ID: c0ffee125847
Revises: a09bc4e8f1d0
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c0ffee125847"
down_revision: Union[str, None] = "a09bc4e8f1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stage_statistics",
        sa.Column("stage_url", sa.String, primary_key=True),
        sa.Column("players", sa.Integer, nullable=False, server_default="0"),
        sa.Column("audiences", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_on",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("stage_statistics")
