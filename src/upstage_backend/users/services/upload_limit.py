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
  * A NULL `upload_limit` means "no per-user override" (see
    AssetService.upload_file); only the server-wide caps apply.

Kept dependency-free (env + the role constants) so it can be imported by
the asset service, the GraphQL resolvers and the DB-free unit tests alike.
"""

from typing import Optional

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
    The per-user byte cap that `AssetService.upload_file` must enforce for
    a user with this role/stored limit, or None when no per-user cap
    applies (admins, or a NULL stored limit).
    """
    if _role_as_int(role) in UNCAPPED_ROLES:
        return None
    return upload_limit


def effective_upload_limit(role, upload_limit: Optional[int]) -> int:
    """
    The largest file (in bytes) this user can actually upload, as a
    concrete number the client can compare a File.size against: the
    per-user cap when one applies, otherwise the server-wide maximum.
    """
    cap = per_user_upload_cap(role, upload_limit)
    return SERVER_UPLOAD_MAX if cap is None else int(cap)
