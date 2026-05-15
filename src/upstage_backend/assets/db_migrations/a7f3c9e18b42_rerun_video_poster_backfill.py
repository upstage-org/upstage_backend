"""Re-run video poster backfill after fixing migrate container uploads + ffmpeg.

Revision ID: a7f3c9e18b42
Revises: e3b2a48fd17c
Create Date: 2026-05-14

The first backfill revision (``e3b2a48fd17c``) ran inside ``upstage_db_migrate``
before that service mounted the host uploads volume, so it walked an empty tree
(and the slim image had no ffmpeg, so uploads could not generate posters either).

This revision is intentionally **filesystem-only** (no SQL), idempotent, and
skipped in Alembic offline mode — matching the semantics of ``e3b2a48fd17c``.
Downgrade is a no-op.

See ``app_containers/docker-compose.yaml``: ``upstage_db_migrate`` must use the
same ``/usr/app/uploads`` bind mount as ``upstage_backend``.
"""

from typing import Sequence, Union

from alembic import context

from upstage_backend.global_config.logger import logger


revision: str = "a7f3c9e18b42"
down_revision: Union[str, None] = "e3b2a48fd17c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():
        logger.info(
            "rerun_video_poster_backfill: offline mode, skipping filesystem work"
        )
        return

    from upstage_backend.files.video_poster import backfill_video_posters

    backfill_video_posters()


def downgrade() -> None:
    pass
