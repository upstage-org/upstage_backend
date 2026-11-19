"""config.name unique

`SettingService.save_config` is a get-or-create on `config.name` with no
constraint behind it, so two concurrent first saves of a key (e.g. the
foyer's pinned stages) could leave two rows and reads then picked one at
random. Keep the oldest row of each name and make the name unique.

Revision ID: d4e6f8a0b2c4
Revises: b9d2f4a6c8e0
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4e6f8a0b2c4"
down_revision: Union[str, None] = "b9d2f4a6c8e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM config a
        USING config b
        WHERE a.name = b.name AND a.id > b.id
        """
    )
    op.create_unique_constraint("uq_config_name", "config", ["name"])


def downgrade() -> None:
    op.drop_constraint("uq_config_name", "config", type_="unique")
