# -*- coding: iso8859-15 -*-
import os
import sys

from global_config.schema import config_graphql_endpoints

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

import random
from main import app
from global_config import global_session, JWT_HEADER_NAME
import pytest
from authentication.http.schema import auth_graphql_app
from global_config import encrypt
from users.db_models.user import PLAYER, SUPER_ADMIN, UserModel
from faker import Faker

@pytest.mark.anyio
class TestAuthenticationController:
    login_query = """
        mutation Login($payload: LoginInput!) {
            login(payload: $payload) {
                user_id
                access_token
                refresh_token
                role
                first_name
                groups {
                    id
                    name
                }
                username
                title
            }
        }
        """

    refresh_token_query = """
        mutation refreshToken {
            refreshToken {
                access_token
            }
        }
    """

    async def test_01_login_with_invalid_credentials(self, client):
        variables = {
            "payload": {"username": Faker().email(), "password": "testpassword"}
        }
        response = client.post(
            "/api/studio_graphql", json={"query": self.login_query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["message"] == "Incorrect username or password. Please try again."

    async def test_02_login_successfully(self, client):
        email = f"{random.randint(1, 1000)}{Faker().email()}"
        user = UserModel(
            username=email,
            password=encrypt(f"testpassword"),
            email=email,
            active=True,
            role=SUPER_ADMIN,
        )
        global_session.add(user)
        global_session.commit()
        global_session.flush()
        variables = {"payload": {"username": email, "password": "testpassword"}}
        response = client.post(
                     "/api/studio_graphql", json={"query": self.login_query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "login" in data["data"]
        assert data["data"]["login"]["username"] == email
        return data

    async def test_player_login_successfully(self, client):
        email = f"{random.randint(1, 1000)}{Faker().email()}"
        user = UserModel(
            username=email,
            password=encrypt(f"testpassword"),
            email=email,
            active=True,
            role=PLAYER,
        )
        global_session.add(user)
        global_session.commit()
        global_session.close()
        variables = {"payload": {"username": email, "password": "testpassword"}}
        response = client.post(
            "/api/studio_graphql", json={"query": self.login_query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "login" in data["data"]
        assert data["data"]["login"]["username"] == email
        return data

    async def test_03_refresh_token_successfully(self, client):
        email = f"{random.randint(1, 1000)}{Faker().email()}"
        user = UserModel(
            username=email,
            password=encrypt(f"testpassword"),
            email=email,
            active=True,
            role=SUPER_ADMIN,
        )
        global_session.add(user)
        global_session.commit()
        global_session.close()

        variables = {"payload": {"username": email, "password": "testpassword"}}
        response = client.post(
            "/api/studio_graphql", json={"query": self.login_query, "variables": variables}
        )
        data = response.json()
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }
        response = client.post(
            "/api/studio_graphql", json={"query": self.refresh_token_query}, headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "refreshToken" in data["data"]

    def test_04_refresh_token_failed(self, client):
        headers = {
            "Authorization": f"Bearer invalid_token",
            JWT_HEADER_NAME: "invalid_token",
        }
        response = client.post(
            "/api/studio_graphql", json={"query": self.refresh_token_query}, headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["message"] == "Invalid refresh token"

    async def test_05_logout(self, client):
        email = f"{random.randint(1, 1000)}{Faker().email()}"
        user = UserModel(
            username=email,
            password=encrypt(f"testpassword"),
            email=email,
            active=True,
            role=SUPER_ADMIN,
        )
        global_session.add(user)
        global_session.commit()
        global_session.close()

        variables = {"payload": {"username": email, "password": "testpassword"}}
        response = client.post(
            "/api/studio_graphql", json={"query": self.login_query, "variables": variables}
        )
        data = response.json()
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        query = """
        mutation Logout {
            logout
        }
        """
        response = client.post("/api/studio_graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert data["data"]["logout"] == "Logged out"

    async def test_06_logout_failed(self, client):
        headers = {
            "Authorization": f"Bearer invalid_token",
            JWT_HEADER_NAME: "invalid_token",
        }

        query = """
        mutation Logout {
            logout
        }
        """
        response = client.post("/api/studio_graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["message"] == "Invalid access token"

    def get_headers(self, client, role):
        email = f"{random.randint(1, 1000)}{Faker().email()}"
        user = UserModel(
            username=email,
            password=encrypt(f"testpassword"),
            email=email,
            active=True,
            role=role,
        )
        global_session.add(user)
        global_session.commit()
        global_session.close()

        variables = {"payload": {"username": email, "password": "testpassword"}}
        response = client.post(
            "/api/studio_graphql", json={"query": self.login_query, "variables": variables}
        )
        data = response.json()
        return {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }
