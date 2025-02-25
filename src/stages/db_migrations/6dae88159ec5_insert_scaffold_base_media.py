"""Insert Scaffold Base Media

Revision ID: 6dae88159ec5
Revises: eb504467a5d7
Create Date: 2025-02-24 18:11:09.592396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from stages.scripts.scaffold_base_media import create_demo_media, create_demo_stage, create_demo_users, scaffold_foyer, scaffold_system_configuration


# revision identifiers, used by Alembic.
revision: str = '6dae88159ec5'
down_revision: Union[str, None] = 'eb504467a5d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    create_demo_media()
    create_demo_stage()
    create_demo_users()
    scaffold_foyer()
    scaffold_system_configuration()
    pass


def downgrade() -> None:
    pass
