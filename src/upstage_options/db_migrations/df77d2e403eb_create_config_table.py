"""Create Config Table

Revision ID: df77d2e403eb
Revises: 25e6a2e462ab
Create Date: 2024-09-06 20:01:55.098610

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "df77d2e403eb"
down_revision: Union[str, None] = "25e6a2e462ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "config",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True, default=None),
        sa.Column(
            "created_on",
            sa.TIMESTAMP(),
            server_default=sa.text("(now() at time zone 'utc')"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("config")
