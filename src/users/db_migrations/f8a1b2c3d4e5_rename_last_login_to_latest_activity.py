"""Rename last_login to latest_activity

Revision ID: f8a1b2c3d4e5
Revises: eb504467a5d7
Create Date: 2025-02-04

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f8a1b2c3d4e5"
down_revision: Union[str, None] = "f6e7b37dc826"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "upstage_user",
        "last_login",
        new_column_name="latest_activity",
    )


def downgrade() -> None:
    op.alter_column(
        "upstage_user",
        "latest_activity",
        new_column_name="last_login",
    )
