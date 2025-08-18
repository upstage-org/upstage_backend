# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

import pytest
from authentication.tests.auth_test import TestAuthenticationController
from global_config.env import JWT_HEADER_NAME
from faker import Faker

test_AuthenticationController = TestAuthenticationController()

email = Faker().email()


@pytest.mark.anyio
class TestUserController:
    create_user_query = """
        mutation CreateUser($inbound: CreateUserInput!) {
            createUser(inbound: $inbound) {
                user {
                    id
                    username
                    email
                    firstName
                    lastName
                    intro
                }
            }
        }
    """

    async def test_01_create_user(self, client):
        variables = {
            "inbound": {
                "username": email,
                "password": "testpassword",
                "email": email,
                "firstName": "Test",
                "lastName": "User",
                "intro": "I am a test user",
                "token": "testtoken",
            }
        }

        response = client.post(
            "/api/studio_graphql",
            json={"query": self.create_user_query, "variables": variables},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "createUser" in data["data"]
        assert "id" in data["data"]["createUser"]["user"]
        assert (
            "username" in data["data"]["createUser"]["user"]
            and data["data"]["createUser"]["user"]["username"]
            == variables["inbound"]["username"]
        )

    async def test_02_create_user_failed(self, client):
        variables = {
            "inbound": {
                "username": email,
                "password": "testpassword",
                "email": email,
                "firstName": "Test",
                "lastName": "User",
                "intro": "I am a test user",
                "token": "testtoken",
            }
        }

        response = client.post(
            "/api/studio_graphql",
            json={"query": self.create_user_query, "variables": variables},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert "data" in data
        assert "createUser" in data["data"]
        assert data["data"]["createUser"] is None

    async def test_03_get_current_user(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)

        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        query = """
            query {
                currentUser {
                    id
                    username
                    email
                    firstName
                    lastName
                    intro
                }
            }
        """

        response = client.post("/api/studio_graphql", json={"query": query}, headers=headers)
        data = response.json()

        assert "errors" not in data
        assert "data" in data
        assert "currentUser" in data["data"]
        assert data["data"]["currentUser"] is not None
