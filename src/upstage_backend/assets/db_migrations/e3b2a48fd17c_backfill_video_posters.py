"""Backfill first-frame posters for existing videos

Revision ID: e3b2a48fd17c
Revises: c1a4d3f7e29b
Create Date: 2026-05-13 20:40:00.000000

The "Video" toolbox switched from silently-looping playback to a
static first-frame thumbnail in the same release (see
``upstage_backend.files.video_poster``). Newly-uploaded videos get a
poster generated synchronously at upload time, but every video
already on disk predates that hook and would render as a blank
thumbnail until the operator manually ran
``scripts/backfill_video_posters.py``.

Running the backfill as part of ``alembic upgrade`` removes that
manual step: deploying the new release also produces posters for
every legacy video, so the toolbox looks right immediately.

Properties:
    * **Filesystem-only.** No DB mutation; runs no SQL. Alembic
      tracks this revision in ``alembic_version`` as usual so it
      isn't re-run on subsequent upgrades.
    * **Idempotent.** Skips videos that already have a poster.
    * **Best-effort.** If ffmpeg is missing, the upload folder
      doesn't exist (fresh install), or an individual video fails,
      the migration logs and continues. Migrations must not fail for
      operational reasons unrelated to schema correctness.
    * **Offline-mode safe.** ``alembic upgrade --sql`` (which only
      emits SQL without touching anything) is detected and the
      backfill is skipped — there's no filesystem to mutate.

Downgrade is a no-op. The generated JPGs are harmless if left on
disk; if you really want them gone, deleting them by hand is
trivial and we don't want a downgrade to silently destroy
operator-visible artefacts.
"""

from typing import Sequence, Union

from alembic import context

from upstage_backend.global_config.logger import logger


revision: str = "e3b2a48fd17c"
down_revision: Union[str, None] = "c1a4d3f7e29b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():
        # `alembic upgrade --sql` generates SQL output without
        # connecting to anything; touching the filesystem here would
        # be wrong (and meaningless — the SQL is generated on a host
        # that may not have the upload volume mounted).
        logger.info(
            "backfill_video_posters: offline mode, skipping filesystem work"
        )
        return

    # Imported inside the function so that an `alembic revision`
    # autogenerate run that imports this module doesn't accidentally
    # walk the upload folder. The import is cheap.
    from upstage_backend.files.video_poster import backfill_video_posters

    backfill_video_posters()


def downgrade() -> None:
    # See module docstring: deliberately a no-op.
    pass
