"""
Shared authorization helpers for GraphQL resolvers and services.

`current_user` on ``request.state`` is a plain dict (see
decorators/authenticated.py); services usually receive a transient
``UserModel`` built from it. Both shapes are accepted here.
"""

from graphql import GraphQLError

from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN

FORBIDDEN_MESSAGE = "You are not authorized to perform this action!"


def role_of(user) -> int:
    role = user.get("role") if isinstance(user, dict) else getattr(user, "role", None)
    try:
        return int(role)
    except (TypeError, ValueError):
        return -1


def user_id_of(user):
    raw = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def is_admin(user) -> bool:
    return role_of(user) in (ADMIN, SUPER_ADMIN)


def is_super_admin(user) -> bool:
    return role_of(user) == SUPER_ADMIN


def require_owner_or_admin(user, owner_id, message: str = FORBIDDEN_MESSAGE) -> None:
    """Raise unless `user` is an admin or owns the row whose owner is `owner_id`."""
    if is_admin(user):
        return
    uid = user_id_of(user)
    try:
        owner = int(owner_id)
    except (TypeError, ValueError):
        owner = None
    if uid is None or owner is None or uid != owner:
        raise GraphQLError(message)
