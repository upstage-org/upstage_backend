# -*- coding: iso8859-15 -*-
"""
Per-user upload cap policy.

Rules (product decision, 2026-09-05):
  * Admins and super admins are never subject to a per-user cap. The only
    limits that still apply to them are the server-wide ones
    (FileHandling.validate_file_size -> OTHER_MEDIA_MAX_SIZE / VIDEO_MAX_SIZE,
    and nginx client_max_body_size, both 500M).
  * Everyone else is capped by `upstage_user.upload_limit`, which defaults
    to 1 MiB and which an admin may raise or lower per player.
  * A NULL `upload_limit` on a non-admin counts as the 1 MiB default
    (2026-09-11). Until then NULL meant "no per-user cap", which was only
    ever intended for the migration-seeded admin -- admins are exempt by
    role now, so for a player it was just a silent hole: Player Management
    showed nothing useful and the server let anything up to 500 MiB through.

Every upload path (uploadFile, uploadMedia, updateMedia's replacement
file and multiframe frames) must go through `enforce_upload_cap` so the
rule cannot drift between them again.

Kept light (env + the role constants + GraphQLError) so it can be imported
by the services, the GraphQL resolvers and the DB-free unit tests alike.
"""

from typing import Optional

from graphql import GraphQLError

from upstage_backend.global_config.env import OTHER_MEDIA_MAX_SIZE
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN

DEFAULT_PLAYER_UPLOAD_LIMIT = 1024 * 1024

# Roles that bypass the per-user cap entirely.
UNCAPPED_ROLES = frozenset({ADMIN, SUPER_ADMIN})

# The largest single upload the server accepts regardless of role
# (FileHandling.validate_file_size; nginx's client_max_body_size matches).
SERVER_UPLOAD_MAX = OTHER_MEDIA_MAX_SIZE


def _role_as_int(role) -> Optional[int]:
    try:
        return int(role)
    except (TypeError, ValueError):
        return None


def per_user_upload_cap(role, upload_limit: Optional[int]) -> Optional[int]:
    """
    The per-user byte cap to enforce for a user with this role/stored
    limit, or None when no per-user cap applies (admins). A NULL stored
    limit on anyone else is the 1 MiB default.
    """
    if _role_as_int(role) in UNCAPPED_ROLES:
        return None
    if upload_limit is None:
        return DEFAULT_PLAYER_UPLOAD_LIMIT
    return int(upload_limit)


def effective_upload_limit(role, upload_limit: Optional[int]) -> int:
    """
    The largest file (in bytes) this user can actually upload, as a
    concrete number the client can compare a File.size against: the
    per-user cap when one applies, otherwise the server-wide maximum.
    """
    cap = per_user_upload_cap(role, upload_limit)
    return SERVER_UPLOAD_MAX if cap is None else int(cap)


def _cap_label_mb(cap: int) -> str:
    """Label a cap as "1MB" for whole mebibytes, "1.5MB" otherwise (the old
    int() truncation reported a 1.5 MiB cap as "1MB")."""
    mb = cap / (1024 * 1024)
    return f"{int(mb)}MB" if mb == int(mb) else f"{mb:g}MB"


def enforce_upload_cap(role, upload_limit: Optional[int], file_size: int) -> None:
    """
    Raise the user-facing GraphQLError when `file_size` (decoded bytes)
    exceeds the per-user cap for this role/stored limit. No-op for admins.
    The server-wide per-extension caps (FileHandling.validate_file_size)
    are enforced separately by the file write itself.
    """
    cap = per_user_upload_cap(role, upload_limit)
    if cap is not None and file_size > cap:
        raise GraphQLError(f"File size must be under {_cap_label_mb(cap)}.")
