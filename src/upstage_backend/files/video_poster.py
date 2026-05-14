"""First-frame poster generation for uploaded videos.

Why posters at all
------------------
The performer-side "Video" toolbox used to render a `<video>` element
without a poster and relied on the browser's poster-frame behaviour
to show a stand-in. Modern Firefox/Chromium/Brave media policies
either render a black rectangle or force the controls overlay until
the user clicks, so that approach was abandoned in favour of muted
looping playback. Looping is reliable but it isn't what users want
out of a thumbnail — they want a single still frame.

This module extracts the very first decoded frame of the video
server-side via ffmpeg and writes it next to the source file as
`<video_path>.poster.jpg`. The frontend can then point the `<video
poster="...">` attribute at that JPG, gets a real static
thumbnail in every browser, and drops the looping playback.

Best-effort by design
---------------------
A missing or broken ffmpeg installation must never break uploads —
losing an uploaded video because the operator forgot to install
ffmpeg would be a much worse failure mode than a missing thumbnail.
All exceptions (ffmpeg not on PATH, non-zero exit, timeout, codec
errors) are caught and logged; the function returns ``None`` and the
caller proceeds.
"""

import os
import shutil
import subprocess

from upstage_backend.global_config.logger import logger


# Hard cap to keep a hostile / corrupt upload from pinning a worker.
# 30s is well above any reasonable first-frame extraction time for
# the file sizes accepted by FileHandling.validate_file_size.
_FFMPEG_TIMEOUT_SECONDS = 30


# Mirrors the AssetService._VIDEO_EXTENSIONS / FileHandling
# validate_file_size allowlist. Kept here too so the backfill walker
# and the upload-time hook agree on what counts as a video without
# pulling in the assets service (which would be a layering inversion
# — the files package must not depend on assets).
VIDEO_EXTENSIONS = (".mp4", ".webm", ".opgg", ".3gp", ".flv")


def poster_path_for(video_path: str) -> str:
    """Canonical poster path for a given video file.

    Centralised so the upload-time generator, the backfill script, and
    any future consumer agree on naming. The convention — append
    `.poster.jpg` to the *full* original filename including its
    extension — keeps posters and videos sorted next to each other in
    listings, avoids collisions between `foo.mp4` and `foo.webm` in
    the same directory, and makes the frontend's URL derivation
    trivial (string concat, not extension swap).
    """
    return f"{video_path}.poster.jpg"


def extract_first_frame(video_path: str) -> str | None:
    """Extract the first frame of ``video_path`` as a JPG poster.

    Returns the absolute path of the generated poster on success, or
    ``None`` if extraction was skipped or failed for any reason. The
    caller MUST treat the return value as advisory only and not gate
    upload success on it.
    """
    if not os.path.isfile(video_path):
        logger.warning(
            "video_poster: source not found, skipping: {}", video_path
        )
        return None

    out_path = poster_path_for(video_path)
    if os.path.exists(out_path):
        # Idempotent: re-running the backfill or an accidental double
        # upload doesn't redo the work or risk a partial overwrite.
        return out_path

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        logger.warning(
            "video_poster: ffmpeg not on PATH; skipping poster for {}",
            video_path,
        )
        return None

    # `-ss 0 -i ... -frames:v 1` seeks to the first frame and writes
    # exactly one image. `-q:v 5` is JPEG quality (1=best, 31=worst);
    # 5 is the sweet spot for toolbox thumbnails — visually clean at
    # the small sizes the toolbox renders, well under 100 KB for most
    # SD-ish source material. `-y` overwrites any partial leftover
    # from a previous interrupted run. `-an` disables audio decode
    # entirely (we only want a still frame).
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-ss",
        "0",
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-q:v",
        "5",
        "-an",
        out_path,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=_FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "video_poster: ffmpeg timed out after {}s for {}",
            _FFMPEG_TIMEOUT_SECONDS,
            video_path,
        )
        # Best-effort cleanup of any half-written output. If ffmpeg
        # was killed mid-write we don't want to leave a broken JPG on
        # disk that the frontend would happily try to render.
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        return None
    except Exception:
        logger.exception(
            "video_poster: ffmpeg invocation failed for {}", video_path
        )
        return None

    if proc.returncode != 0 or not os.path.exists(out_path):
        # Log stderr at warning level (it can be noisy for files with
        # codec quirks; we don't want to spam exception traces).
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        logger.warning(
            "video_poster: ffmpeg returned {} for {}; stderr: {}",
            proc.returncode,
            video_path,
            stderr[:500],
        )
        return None

    return out_path


def iter_video_files(root: str):
    """Yield absolute paths of every recognised video under ``root``.

    Walks recursively. Skips files that already look like generated
    posters (``*.poster.jpg``) — belt-and-braces in case someone
    renames a video to end in `.jpg` (which shouldn't happen, but the
    cost of guarding is one ``endswith`` per file).
    """
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            if name.endswith(".poster.jpg"):
                continue
            yield os.path.join(dirpath, name)


def backfill_video_posters(root: str | None = None) -> dict:
    """Generate posters for every video under ``root`` that lacks one.

    Shared by:
      * ``scripts/backfill_video_posters.py`` (manual CLI invocation)
      * the Alembic backfill migration (runs automatically on
        ``alembic upgrade``)

    Idempotent and best-effort. Designed to be safe to call from a
    migration: a missing ``root`` or an absent ffmpeg only logs and
    returns counts; it never raises.

    Returns a counts dict so callers can log a summary:
        {"scanned": int, "generated": int, "skipped": int, "failed": int}

    ``root=None`` resolves to the default ``UPLOAD_USER_CONTENT_FOLDER``.
    """
    # Late import so importing this module from contexts that don't
    # need the upload folder (e.g. unit tests of ``extract_first_frame``
    # against a tmpdir) doesn't drag in the global env constants.
    if root is None:
        from upstage_backend.global_config.env import UPLOAD_USER_CONTENT_FOLDER

        root = UPLOAD_USER_CONTENT_FOLDER

    counts = {"scanned": 0, "generated": 0, "skipped": 0, "failed": 0}

    if not root or not os.path.isdir(root):
        # Common on dev boxes or fresh installs: the upload folder
        # doesn't exist yet, so there's nothing to backfill. Don't
        # error out — that would block ``alembic upgrade`` for no
        # reason.
        logger.info(
            "video_poster: backfill root not found, skipping: {}", root
        )
        return counts

    for video_path in iter_video_files(root):
        counts["scanned"] += 1
        if os.path.exists(poster_path_for(video_path)):
            counts["skipped"] += 1
            continue
        if extract_first_frame(video_path):
            counts["generated"] += 1
        else:
            counts["failed"] += 1

    logger.info(
        "video_poster: backfill complete root={} {}", root, counts
    )
    return counts
