#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""Generate poster JPGs for every existing uploaded video.

Manual CLI wrapper around
``upstage_backend.files.video_poster.backfill_video_posters``. The
same function also runs automatically as part of the Alembic
migration ``backfill_video_posters`` on ``alembic upgrade``, so this
script is now primarily for:
    * dev boxes where you skipped the migration but want posters,
    * one-off recovery after restoring uploads from backup, or
    * running it again after manually copying new videos into the
      upload folder out-of-band.

Properties (inherited from the shared helper):
    * Idempotent — re-running skips files that already have a poster.
    * Read/write only — no database mutation.
    * Best-effort — a missing ffmpeg or a single broken video logs a
      warning but doesn't abort the rest of the scan.

Usage:
    python scripts/backfill_video_posters.py
    python scripts/backfill_video_posters.py --root /custom/path/to/uploads
"""

import argparse
import sys

import loguru  # noqa: F401  # entrypoint: load loguru before upstage

from upstage_backend.files.video_poster import backfill_video_posters
from upstage_backend.global_config.env import UPLOAD_USER_CONTENT_FOLDER
from upstage_backend.global_config.logger import logger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=UPLOAD_USER_CONTENT_FOLDER,
        help=(
            "Upload root to scan. Defaults to UPLOAD_USER_CONTENT_FOLDER "
            "from the environment."
        ),
    )
    args = parser.parse_args()

    counts = backfill_video_posters(args.root)

    logger.info(
        "backfill_video_posters: scanned={scanned} generated={generated} "
        "skipped={skipped} failed={failed}",
        **counts,
    )

    # Non-zero exit only if we found videos and *every* one failed —
    # partial failure is normal (a single corrupt file shouldn't block
    # the rest of the backfill from being marked successful).
    if counts["scanned"] > 0 and counts["generated"] == 0 and counts["failed"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
