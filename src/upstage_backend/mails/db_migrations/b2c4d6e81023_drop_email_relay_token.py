"""Drop email_relay_token if present (remote mail relay removed)

Revision ID: b2c4d6e81023
Revises: a7c3e9012b4d
Create Date: 2026-05-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b2c4d6e81023"
down_revision: Union[str, None] = "a7c3e9012b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_email_relay_token_from_server")
    op.execute("DROP TABLE IF EXISTS email_relay_token")


def downgrade() -> None:
    pass
