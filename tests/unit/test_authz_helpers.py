"""global_config/helpers/authz.py: role and ownership checks shared by resolvers."""

import pytest
from graphql import GraphQLError

from upstage_backend.global_config.helpers.authz import (
    is_admin,
    is_super_admin,
    require_owner_or_admin,
    role_of,
    user_id_of,
)
from upstage_backend.users.db_models.user import ADMIN, GUEST, PLAYER, SUPER_ADMIN


class _User:
    def __init__(self, id, role):
        self.id = id
        self.role = role


@pytest.mark.parametrize(
    "user, expected",
    [
        ({"id": 1, "role": ADMIN}, True),
        ({"id": 1, "role": str(SUPER_ADMIN)}, True),
        ({"id": 1, "role": PLAYER}, False),
        (_User(2, GUEST), False),
        (_User(2, SUPER_ADMIN), True),
        ({"id": 1}, False),
        ({"id": 1, "role": "abc"}, False),
    ],
)
def test_is_admin_handles_dicts_models_and_bad_roles(user, expected):
    assert is_admin(user) is expected


def test_is_super_admin_is_stricter_than_is_admin():
    assert is_super_admin({"role": SUPER_ADMIN}) is True
    assert is_super_admin({"role": ADMIN}) is False


def test_role_and_user_id_coercion():
    assert role_of({"role": "8"}) == ADMIN
    assert role_of({}) == -1
    assert user_id_of({"id": "42"}) == 42
    assert user_id_of({"id": None}) is None
    assert user_id_of(_User("x", PLAYER)) is None


def test_require_owner_or_admin_allows_owner_and_admin():
    require_owner_or_admin({"id": 7, "role": PLAYER}, 7)
    require_owner_or_admin({"id": 1, "role": ADMIN}, 7)
    require_owner_or_admin(_User(1, SUPER_ADMIN), "7")


@pytest.mark.parametrize("owner_id", [8, "8", None, "nope"])
def test_require_owner_or_admin_rejects_others(owner_id):
    with pytest.raises(GraphQLError, match="custom"):
        require_owner_or_admin({"id": 7, "role": PLAYER}, owner_id, "custom message")
