"""
Login lifetime by role: JWT_ADMIN_TOKEN_DAYS for admins and super admins,
JWT_USER_TOKEN_DAYS for everyone else. The refresh token is issued with the
same lifetime as the access token.
"""

from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError

from upstage_backend.authentication.services import auth as auth_module
from upstage_backend.authentication.services.auth import AuthenticationService
from upstage_backend.global_config.app_settings import Settings
from upstage_backend.global_config.env import ALGORITHM, SECRET_KEY
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.users.db_models.user import ADMIN, GUEST, PLAYER, SUPER_ADMIN, UserModel


@pytest.fixture
def lifetimes(monkeypatch):
    monkeypatch.setattr(auth_module, "JWT_ADMIN_TOKEN_DAYS", 30)
    monkeypatch.setattr(auth_module, "JWT_USER_TOKEN_DAYS", 2)


def _remaining(token: str) -> timedelta:
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return timedelta(seconds=claims["exp"] - utcnow().timestamp())


@pytest.mark.parametrize(
    "role, days",
    [(SUPER_ADMIN, 30), (ADMIN, 30), (PLAYER, 2), (GUEST, 2), (None, 2)],
)
def test_lifetime_by_role(lifetimes, role, days):
    assert AuthenticationService.token_lifetime(role) == timedelta(days=days)


@pytest.mark.parametrize("role, days", [(SUPER_ADMIN, 30), (ADMIN, 30), (PLAYER, 2)])
def test_both_tokens_carry_the_role_lifetime(lifetimes, role, days):
    user = UserModel(id=7, role=role)
    access, refresh = AuthenticationService.__new__(AuthenticationService).create_token_pair(user)

    for token in (access, refresh):
        assert abs(_remaining(token) - timedelta(days=days)) < timedelta(minutes=1)

    access_claims = jwt.decode(access, SECRET_KEY, algorithms=[ALGORITHM])
    refresh_claims = jwt.decode(refresh, SECRET_KEY, algorithms=[ALGORITHM])
    assert access_claims["user_id"] == refresh_claims["user_id"] == 7
    assert "type" not in access_claims
    assert refresh_claims["type"] == "refresh"


def test_lifetimes_follow_the_settings(monkeypatch):
    monkeypatch.setattr(auth_module, "JWT_ADMIN_TOKEN_DAYS", 7)
    monkeypatch.setattr(auth_module, "JWT_USER_TOKEN_DAYS", 1)
    assert AuthenticationService.token_lifetime(ADMIN) == timedelta(days=7)
    assert AuthenticationService.token_lifetime(PLAYER) == timedelta(days=1)


def test_settings_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("JWT_ADMIN_TOKEN_DAYS", raising=False)
    monkeypatch.delenv("JWT_USER_TOKEN_DAYS", raising=False)
    assert (Settings().JWT_ADMIN_TOKEN_DAYS, Settings().JWT_USER_TOKEN_DAYS) == (30, 2)

    monkeypatch.setenv("JWT_USER_TOKEN_DAYS", "5")
    assert Settings().JWT_USER_TOKEN_DAYS == 5
    assert Settings(JWT_ADMIN_TOKEN_DAYS=14).JWT_ADMIN_TOKEN_DAYS == 14


@pytest.mark.parametrize("value", ["0", "-1", "soon"])
def test_a_lifetime_must_be_a_positive_number_of_days(monkeypatch, value):
    monkeypatch.setenv("JWT_USER_TOKEN_DAYS", value)
    with pytest.raises(ValidationError):
        Settings()


def test_every_token_is_distinct(lifetimes):
    service = AuthenticationService.__new__(AuthenticationService)
    user = UserModel(id=7, role=PLAYER)
    first, second = service.create_token_pair(user), service.create_token_pair(user)
    assert len({*first, *second}) == 4
