"""
Filesystem path containment for user-supplied media locations.

Asset ``file_location`` values, frame lists and media-type sub-folders all
come from GraphQL input and are joined onto the uploads root before the
process reads, writes or deletes files. Every such join goes through
``safe_join`` so a ``../`` or absolute component can never escape the root.
"""

import os

from graphql import GraphQLError

INVALID_LOCATION_MESSAGE = "Invalid file location"


def is_safe_relative_path(value) -> bool:
    """True for a non-empty relative path with no ``.``/``..`` components."""
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    normalised = value.replace("\\", "/")
    if normalised.startswith("/"):
        return False
    return all(part not in ("", ".", "..") for part in normalised.split("/"))


def safe_join(root: str, *parts: str, message: str = INVALID_LOCATION_MESSAGE) -> str:
    """Join ``parts`` under ``root`` and refuse anything that resolves outside it."""
    root_real = os.path.realpath(root)
    for part in parts:
        if not isinstance(part, str) or "\x00" in part:
            raise GraphQLError(message)
    candidate = os.path.realpath(os.path.join(root_real, *parts))
    if candidate != root_real and not candidate.startswith(root_real + os.sep):
        raise GraphQLError(message)
    return candidate


def try_safe_join(root: str, *parts: str):
    """``safe_join`` that returns ``None`` instead of raising (cleanup paths)."""
    try:
        return safe_join(root, *parts)
    except GraphQLError:
        return None
