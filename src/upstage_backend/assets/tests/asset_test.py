# -*- coding: iso8859-15 -*-


import base64
import os

import pytest
from upstage_backend.global_config.env import JWT_HEADER_NAME, UPLOAD_USER_CONTENT_FOLDER
from upstage_backend.global_config import get_session
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController as _TestAuthenticationController
from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.stages.tests.test_stage import TestStageController as _TestStageController
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.users.db_models.user import PLAYER, UserModel


def load_base64_from_image(image_path):
    # Paths are given relative to the src tree ("src/assets/tests/images/..."),
    # which only resolves when pytest's cwd is the package root; resolve them
    # against this file instead so the suite runs from /usr/app too.
    if not os.path.isabs(image_path) and not os.path.exists(image_path):
        image_path = os.path.join(os.path.dirname(__file__), "images", os.path.basename(image_path))
    with open(image_path, "rb") as image_file:
        base64_encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return base64_encoded


test_AuthenticationController = _TestAuthenticationController()


def newest_test_asset():
    """The most recent asset a test created (they are all named "test").
    Never fall back to an unfiltered .first(): against a shared database that
    is a real user's media (the dev Demo Stage lost its cover, backdrop,
    streams and audio that way on 2026-09-10)."""
    return (
        get_session()
        .query(AssetModel)
        .filter(AssetModel.name == "test")
        .order_by(AssetModel.id.desc())
        .first()
    )
test_stageController = _TestStageController()


@pytest.mark.anyio
class TestAssetController:
    mutation_query = """
        mutation UploadFile($base64: String!, $filename: String!) {
            uploadFile(base64: $base64, filename: $filename) {
                url
            }
        }
    """

    async def test_01_upload_file_successfully(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)

        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        variables = {
            "base64": f"data:image/jpeg;base64,{load_base64_from_image('src/assets/tests/images/test.png')}",
            "filename": "test.png",
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": self.mutation_query, "variables": variables},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "uploadFile" in data["data"]
        assert "url" in data["data"]["uploadFile"]
        assert data["data"]["uploadFile"]["url"] is not None

        # A raw upload has no asset row, so the fixture sweep cannot find the
        # file - remove it here (they piled up under uploads/image on dev).
        location = data["data"]["uploadFile"]["url"].split("/resources/", 1)[-1].split("?")[0]
        path = os.path.join(UPLOAD_USER_CONTENT_FOLDER, location.lstrip("/"))
        if os.path.isfile(path):
            os.remove(path)

    async def test_02_upload_file_without_authentication(self, client):
        variables = {
            "base64": f"data:image/jpeg;base64,{load_base64_from_image('src/assets/tests/images/test.png')}",
            "filename": "test.png",
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": self.mutation_query, "variables": variables},
        )
        # GraphQL-level errors are answered with HTTP 400 (older builds: 200).
        assert response.status_code in (200, 400)
        data = response.json()
        assert "data" in data
        assert "errors" in data
        assert data["errors"][0]["message"] == "Authenticated Failed"

    async def test_03_save_media_successfully(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)
        assigned_user = await test_AuthenticationController.test_02_login_successfully(client)

        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        mutation_query = """
            mutation SaveMedia($input: SaveMediaInput!) {
                saveMedia(input: $input) {
                    asset {
                        id
                    }
                }
            }
        """

        stage = await test_stageController.test_01_create_stage(client)

        variables = {
            "input": {
                "name": "test",
                "mediaType": "image",
                "urls": ["https://test.com/test.png?download/media"],
                "w": 100,
                "h": 100,
                "tags": ["test"],
                "copyrightLevel": 0,
                "stageAssignments": [{"stageId": stage["id"]}],
                "userIds": [assigned_user["data"]["login"]["user_id"]],
                "owner": data["data"]["login"]["username"],
            }
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert "data" in data
        assert "saveMedia" in data["data"]
        assert "id" in data["data"]["saveMedia"]["asset"]

    async def test_04_save_media_without_authentication(self, client):
        mutation_query = """
            mutation SaveMedia($input: SaveMediaInput!) {
                saveMedia(input: $input) {
                    asset {
                        id
                    }
                }
            }
        """

        stages = get_session().query(StageModel).all()
        users = get_session().query(UserModel).all()

        variables = {
            "input": {
                "name": "test",
                "mediaType": "image",
                "urls": ["https://test.com/test.png"],
                "w": 100,
                "h": 100,
                "tags": ["test"],
                "copyrightLevel": 0,
                "stageAssignments": [{"stageId": stage.id} for stage in stages],
                "userIds": [user.id for user in users],
                "owner": "test",
            }
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
        )
        # GraphQL-level errors are answered with HTTP 400 (older builds: 200).
        assert response.status_code in (200, 400)
        data = response.json()
        assert "data" in data
        assert "errors" in data
        assert data["errors"][0]["message"] == "Authenticated Failed"

    async def test_05_search_assets(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)
        _ = get_session().query(AssetModel).join(UserModel).first()
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        query = """
            query ($input: MediaTableInput!) {
                media(input: $input) {
                    totalCount
                    edges {
                        id
                        name
                    }
                }
            }
        """

        users = get_session().query(UserModel).all()
        stages = get_session().query(StageModel).all()

        response = client.post(
            "/api/studio_graphql",
            json={
                "query": query,
                "variables": {
                    "input": {
                        "page": 1,
                        "limit": 10,
                        "sort": [
                            "ASSET_TYPE_ID_ASC",
                            "OWNER_ID_DESC",
                            "CREATED_ON_ASC",
                            "NAME_ASC",
                        ],
                        "name": "test",
                        "mediaTypes": ["image"],
                        "owners": [user.username for user in users],
                        "stages": [stage.id for stage in stages],
                        "tags": ["test"],
                        "createdBetween": ["2021-01-01", "2026-12-31"],
                    }
                },
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "media" in data["data"]
        assert "totalCount" in data["data"]["media"]
        assert "edges" in data["data"]["media"]
        assert len(data["data"]["media"]["edges"]) > 0

    async def test_06_get_all_medias(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)
        asset = newest_test_asset()
        if asset is None:
            await self.test_03_save_media_successfully(client)
            asset = newest_test_asset()
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        query = """
            query mediaList($mediaType: String, $owner: String) {
                mediaList(mediaType: $mediaType, owner: $owner) {
                        id
                        name
                        assetType {
                            name
                        }
                        owner {
                            id
                            username
                        }

                }
            }
        """

        response = client.post(
            "/api/studio_graphql",
            json={
                "query": query,
                # The first asset on a real DB is whatever happens to be there
                # (an e2e prop, say) — filter by ITS type, not a hard-coded one.
                "variables": {"mediaType": asset.asset_type.name, "owner": asset.owner.username},
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "mediaList" in data["data"]
        assert len(data["data"]["mediaList"]) > 0

    async def test_07_update_media(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)
        asset = newest_test_asset()
        if asset is None:
            await self.test_03_save_media_successfully(client)
            asset = newest_test_asset()

        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        mutation_query = """
            mutation SaveMedia($input: SaveMediaInput!) {
                saveMedia(input: $input) {
                    asset {
                        id
                    }
                }
            }
        """

        variables = {
            "input": {
                "id": asset.id,
                "name": "test",
                "mediaType": "image",
                "urls": ["https://test.com/test.png?download/media"],
                "w": 100,
                "h": 100,
                "tags": ["test"],
                "copyrightLevel": 0,
                "stageAssignments": [],
                "userIds": [],
                "owner": data["data"]["login"]["username"],
            }
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
            headers=headers,
        )

        assert response.status_code == 200

    async def test_08_update_media_failed(self, client):
        data = await test_AuthenticationController.test_player_login_successfully(client)
        asset = newest_test_asset()
        if asset is None:
            await self.test_03_save_media_successfully(client)
            asset = newest_test_asset()

        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        mutation_query = """
            mutation SaveMedia($input: SaveMediaInput!) {
                saveMedia(input: $input) {
                    asset {
                        id
                    }
                }
            }
        """

        variables = {
            "input": {
                "id": asset.id,
                "name": "test",
                "mediaType": "image",
                "urls": ["https://test.com/test.png?download/media"],
                "w": 100,
                "h": 100,
                "tags": ["test"],
                "copyrightLevel": 0,
                "stageAssignments": [],
                "userIds": [],
                "owner": data["data"]["login"]["username"],
            }
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
            headers=headers,
        )

        # Permission error is a GraphQL-level error -> HTTP 400 (older builds: 200).
        assert response.status_code in (200, 400)
        assert "errors" in response.json()

    async def test_09_delete_media_failed(self, client):
        asset = newest_test_asset()
        if asset is None:
            await self.test_03_save_media_successfully(client)
            asset = newest_test_asset()
        data = await test_AuthenticationController.test_player_login_successfully(client)

        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        mutation_query = """
            mutation DeleteMedia($id: ID!) {
                deleteMedia(id: $id) {
                    success
                }
            }
        """

        variables = {"id": asset.id}
        client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
            headers=headers,
        )

        data = await test_AuthenticationController.test_02_login_successfully(client)
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": {"id": 12}},
            headers=headers,
        )

        # "Media not found" is a GraphQL-level error -> HTTP 400 (older builds: 200).
        assert response.status_code in (200, 400)
        assert "errors" in response.json()

    async def test_10_delete_media(self, client):
        await self.test_03_save_media_successfully(client)
        asset = newest_test_asset()
        data = await test_AuthenticationController.test_02_login_successfully(client)
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

        mutation_query = """
            mutation DeleteMedia($id: ID!) {
                deleteMedia(id: $id) {
                    success
                }
            }
        """

        variables = {"id": asset.id}
        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
            headers=headers,
        )
        assert response.status_code == 200

        asset = get_session().query(AssetModel).filter_by(id=asset.id).first()
        assert asset is None

    async def test_11_upload_file_with_large_file(self, client):
        # A PLAYER: admins / super admins are no longer subject to the
        # per-user cap (users.services.upload_limit, 2026-09-05), so the
        # 1 MB rejection this test asserts only applies to non-admins.
        headers = test_AuthenticationController.get_headers(client, PLAYER)

        variables = {
            "base64": f"data:image/jpeg;base64,{load_base64_from_image('src/assets/tests/images/large-file.jpg')}",
            "filename": "large-file.jpg",
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": self.mutation_query, "variables": variables},
            headers=headers,
        )
        # GraphQL-level errors are answered with HTTP 400 (older builds: 200).
        assert response.status_code in (200, 400)
        data = response.json()
        assert "data" in data
        assert "errors" in data
        assert data["errors"][0]["message"] == "File size must be under 1MB."
