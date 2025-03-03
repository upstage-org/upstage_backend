from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String

# revision identifiers, used by Alembic.
revision: str = '0baf970d7eb2'
down_revision: Union[str, None] = 'eb504467a5d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the asset_type table
asset_type_table = table(
    'asset_type',
    column('name', String),
    column('file_location', String)  
)

# List of default asset types
default_asset_types = [
    "stream",
    "backdrop",
    "audio",
    "curtain",
    "prop",
    "avatar",
    "image"
]

def upgrade() -> None:
    conn = op.get_bind()
    for asset_type in default_asset_types:
        result = conn.execute(
            sa.select(asset_type_table.c.name).where(asset_type_table.c.name == asset_type)
        ).fetchone()

        print(result)

        if not result:
            op.bulk_insert(
                asset_type_table,
                [{"name": asset_type, "file_location": ""}]
            )

def downgrade() -> None:
    conn = op.get_bind()
    for asset_type in default_asset_types:
        conn.execute(
            asset_type_table.delete().where(asset_type_table.c.name == asset_type)
        )
