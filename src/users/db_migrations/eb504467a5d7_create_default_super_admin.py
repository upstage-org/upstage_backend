"""Create Default Super Admin

Revision ID: eb504467a5d7
Revises: c4a6bfa6b100
Create Date: 2025-02-21 10:42:34.364797

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Text, Boolean, TIMESTAMP
from datetime import datetime

from global_config.helpers.fernet_crypto import encrypt
from users.db_models.user import SUPER_ADMIN

# revision identifiers, used by Alembic.
revision: str = "eb504467a5d7"
down_revision: Union[str, None] = "c4a6bfa6b100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the user table for inserting data
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


def upgrade() -> None:
    # Insert default super admin
    op.bulk_insert(
        user_table,
        [
            {
                "username": "admin",
                "email": "upstage@gmail.com",
                "password": encrypt(f"Secret@123"),
                "role": SUPER_ADMIN,
                "active": True,
                "created_on": datetime.now(),
                "last_login": None,
                "bin_name": "admin",
                "can_send_email": True,
            }
        ],
    )


def downgrade() -> None:
    # Delete the default super admin
    op.execute(
        "DELETE FROM upstage_user WHERE username='admin' AND email='admin@example.com'"
    )
