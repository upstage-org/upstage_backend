"""Indexes on the foreign keys and lookup columns the list queries filter by.

The baseline schema carried no secondary indexes on the feature tables:
every stage load walked parent_stage / stage_attribute / asset_usage by
sequential scan, and the studio's stage and media lists did the same per
row (2026-09 review, §2.5). These are the columns the ORM relationships
and the service filters actually use; the models declare the same
`index=True` so `alembic check` stays quiet.

`events.topic LIKE '%/<stage>/%'` is deliberately left alone: it needs a
trigram (pg_trgm) index or a stage column on the archive, both of which
are a separate change.

Revision ID: a7c1e2d4f6b8
Revises: c3d5e7f9a1b2
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1e2d4f6b8"
down_revision: Union[str, None] = "c3d5e7f9a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (index name, table, columns)
INDEXES = [
    ("ix_parent_stage_stage_id", "parent_stage", ["stage_id"]),
    ("ix_parent_stage_child_asset_id", "parent_stage", ["child_asset_id"]),
    ("ix_stage_attribute_stage_id_name", "stage_attribute", ["stage_id", "name"]),
    ("ix_stage_owner_id", "stage", ["owner_id"]),
    ("ix_stage_file_location", "stage", ["file_location"]),
    ("ix_asset_owner_id", "asset", ["owner_id"]),
    ("ix_asset_asset_type_id", "asset", ["asset_type_id"]),
    ("ix_asset_file_location", "asset", ["file_location"]),
    ("ix_asset_attribute_asset_id", "asset_attribute", ["asset_id"]),
    ("ix_asset_license_asset_id", "asset_license", ["asset_id"]),
    ("ix_asset_usage_asset_id", "asset_usage", ["asset_id"]),
    ("ix_asset_usage_user_id", "asset_usage", ["user_id"]),
    ("ix_media_tag_asset_id", "media_tag", ["asset_id"]),
    ("ix_media_tag_tag_id", "media_tag", ["tag_id"]),
    ("ix_scene_stage_id", "scene", ["stage_id"]),
    ("ix_performance_stage_id", "performance", ["stage_id"]),
    ("ix_performance_config_owner_id", "performance_config", ["owner_id"]),
    ("ix_live_performance_mqtt_config_performance_id", "live_performance_mqtt_config", ["performance_id"]),
]


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False, if_not_exists=True)


def downgrade() -> None:
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table, if_exists=True)
