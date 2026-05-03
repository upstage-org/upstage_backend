"""Create email_relay_token table (superseded — dropped in b2c4d6e81023)

Revision ID: a7c3e9012b4d
Revises: f6e7b37dc826
Create Date: 2026-05-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c3e9012b4d"
down_revision: Union[str, None] = "f6e7b37dc826"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_relay_token",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("from_server", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="email_relay_token_id"),
        sa.UniqueConstraint("token", name="uq_email_relay_token_token"),
    )
    op.create_index(
        "ix_email_relay_token_from_server",
        "email_relay_token",
        ["from_server"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_email_relay_token_from_server", table_name="email_relay_token")
    op.drop_table("email_relay_token")
