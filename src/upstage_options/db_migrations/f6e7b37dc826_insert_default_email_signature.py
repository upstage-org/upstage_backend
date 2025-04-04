"""Insert default email signature

Revision ID: f6e7b37dc826
Revises: e5f8bc8043a5
Create Date: 2025-04-04 14:27:06.510910

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6e7b37dc826"
down_revision: Union[str, None] = "e5f8bc8043a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    config_table = sa.table(
        "config",
        sa.column("name", sa.String),
        sa.column("value", sa.Text),
    )

    config_defaults = {
        "EMAIL_SIGNATURE": """
                Thank you,
                <br>
                <b style="color: #007011">The UpStage Team!</b>
                </p>
        """,
        "ADDING_EMAIL_SIGNATURE": json.dumps(True),
    }
    for key, value in config_defaults.items():
        exists = connection.execute(
            sa.select(config_table.c.name).where(config_table.c.name == key)
        ).fetchone()
        print(exists)
        if exists is None:
            connection.execute(config_table.insert().values(name=key, value=value))
    

def downgrade() -> None:
    pass
