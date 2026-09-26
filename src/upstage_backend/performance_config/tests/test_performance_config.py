# -*- coding: iso8859-15 -*-


import pytest
from upstage_backend.authentication.tests.auth_test import (
    TestAuthenticationController as _TestAuthenticationController,
)
from upstage_backend.users.db_models.user import PLAYER, SUPER_ADMIN

test_AuthenticationController = _TestAuthenticationController()


def _admin_headers(client):
    return test_AuthenticationController.get_headers(client, SUPER_ADMIN)


@pytest.mark.anyio
class TestPerformanceConfig:
    async def test_00_table_dumps_are_admin_only(self, client):
        """These queries dump whole tables (incl. broker passwords) and used to be public."""
        query = "query { performanceCommunication { id } }"
        anonymous = client.post("/api/studio_graphql", json={"query": query})
        assert anonymous.json()["errors"][0]["message"] == "Authenticated Failed"
        as_player = client.post(
            "/api/studio_graphql",
            json={"query": query},
            headers=test_AuthenticationController.get_headers(client, PLAYER),
        )
        assert as_player.json()["errors"][0]["message"] == "Permission denied"

    async def test_01_get_performance_communication(self, client):
        query = """
            query PerformanceCommunication {
                performanceCommunication {
                    id
                    ownerId
                }

            }
        """
        response = client.post(
            "/api/studio_graphql", json={"query": query}, headers=_admin_headers(client)
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "performanceCommunication" in data["data"]
        assert data["data"]["performanceCommunication"] is not None

    async def test_02_get_performance_config(self, client):
        query = """
            query PerformanceConfig {
                performanceConfig {
                    id

                 }

            }
        """
        response = client.post(
            "/api/studio_graphql", json={"query": query}, headers=_admin_headers(client)
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "performanceConfig" in data["data"]
        assert data["data"]["performanceConfig"] is not None

    async def test_03_get_scene(self, client):
        query = """
            query Scene {
                scene {
                    id
                    ownerId
                }

            }
        """
        response = client.post(
            "/api/studio_graphql", json={"query": query}, headers=_admin_headers(client)
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "scene" in data["data"]
        assert data["data"]["scene"] is not None

    async def test_04_get_parent_stage(self, client):
        query = """
            query ParentStage {
                parentStage {
                    id
                    stageId
                }

            }
        """
        response = client.post(
            "/api/studio_graphql", json={"query": query}, headers=_admin_headers(client)
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data
        assert "parentStage" in data["data"]
        assert data["data"]["parentStage"] is not None
