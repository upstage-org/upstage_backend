"""
Login lifetime by role, as issued by the login and refreshToken mutations:
JWT_ADMIN_TOKEN_DAYS for admins and super admins, JWT_USER_TOKEN_DAYS for
everyone else, for the access token and the refresh token alike.
"""

import random
from datetime import timedelta

import jwt
import pytest
from faker import Faker

from upstage_backend.authentication.services import auth as auth_module
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController
from upstage_backend.global_config.database import ScopedSession
from upstage_backend.global_config.env import ALGORITHM, JWT_HEADER_NAME, SECRET_KEY
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.helpers.password import hash_password
from upstage_backend.users.db_models.user import ADMIN, GUEST, PLAYER, SUPER_ADMIN, UserModel

LOGIN = TestAuthenticationController.login_query
REFRESH = """
    mutation refreshToken {
        refreshToken {
            access_token
            refresh_token
        }
    }
"""


def _days_left(token: str) -> float:
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return (claims["exp"] - utcnow().timestamp()) / timedelta(days=1).total_seconds()


def _login(client, role):
    email = f"{random.randint(1, 1000)}{Faker().email()}"
    with ScopedSession() as s:
        s.add(
            UserModel(
                username=email,
                password=hash_password("testpassword"),
                email=email,
                active=True,
                role=role,
            )
        )
    response = client.post(
        "/api/studio_graphql",
        json={
            "query": LOGIN,
            "variables": {"payload": {"username": email, "password": "testpassword"}},
        },
    )
    return response.json()["data"]["login"]


@pytest.mark.anyio
class TestTokenLifetime:
    @pytest.fixture(autouse=True)
    def _lifetimes(self, monkeypatch):
        monkeypatch.setattr(auth_module, "JWT_ADMIN_TOKEN_DAYS", 30)
        monkeypatch.setattr(auth_module, "JWT_USER_TOKEN_DAYS", 2)

    @pytest.mark.parametrize(
        "role, days", [(SUPER_ADMIN, 30), (ADMIN, 30), (PLAYER, 2), (GUEST, 2)]
    )
    async def test_login_issues_the_role_lifetime(self, client, role, days):
        tokens = _login(client, role)
        assert _days_left(tokens["access_token"]) == pytest.approx(days, abs=0.01)
        assert _days_left(tokens["refresh_token"]) == pytest.approx(days, abs=0.01)

    @pytest.mark.parametrize("role, days", [(ADMIN, 30), (PLAYER, 2)])
    async def test_refresh_issues_the_role_lifetime_again(self, client, role, days):
        tokens = _login(client, role)
        response = client.post(
            "/api/studio_graphql",
            json={"query": REFRESH},
            headers={JWT_HEADER_NAME: tokens["refresh_token"]},
        )
        renewed = response.json()["data"]["refreshToken"]
        assert renewed["refresh_token"] != tokens["refresh_token"]
        assert _days_left(renewed["access_token"]) == pytest.approx(days, abs=0.01)
        assert _days_left(renewed["refresh_token"]) == pytest.approx(days, abs=0.01)

    async def test_a_used_refresh_token_is_refused(self, client):
        tokens = _login(client, PLAYER)
        headers = {JWT_HEADER_NAME: tokens["refresh_token"]}
        first = client.post("/api/studio_graphql", json={"query": REFRESH}, headers=headers)
        assert first.json()["data"]["refreshToken"]["access_token"]

        again = client.post("/api/studio_graphql", json={"query": REFRESH}, headers=headers)
        assert again.json()["errors"][0]["message"] == "Invalid refresh token"
