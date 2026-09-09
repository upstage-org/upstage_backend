# -*- coding: iso8859-15 -*-

import os

import pytest
from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController as _TestAuthenticationController
from upstage_backend.global_config import get_session
from upstage_backend.global_config.env import UPLOAD_USER_CONTENT_FOLDER
from upstage_backend.stages.tests.test_stage import TestStageController as _TestStageController
from upstage_backend.assets.tests.asset_test import (
    TestAssetController as _TestAssetController,
    load_base64_from_image,
    newest_test_asset,
)
from upstage_backend.users.db_models.user import SUPER_ADMIN
import random

test_AuthenticationController = _TestAuthenticationController()
test_StageController = _TestStageController()
test_AssetController = _TestAssetController()


@pytest.mark.anyio
class TestMediaController:
    async def assign_media(self, client, stage_id, media_ids):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        variables = {"input": {"id": stage_id, "mediaIds": media_ids}}

        query = """
            mutation assignMedia($input: AssignMediaInput!) {
                assignMedia(input: $input) {
                    id
                    }
                }
        """

        response = client.post(
            "/api/studio_graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )
        assert response.status_code == 200
        return response

    async def test_01_assign_media(self, client):
        stage = await test_StageController.test_01_create_stage(client)
        await test_AssetController.test_03_save_media_successfully(client)
        assets = get_session().query(AssetModel).filter(AssetModel.name == "test").all()
        response = await self.assign_media(client, stage["id"], [asset.id for asset in assets])

        assert "data" in response.json()
        assert "assignMedia" in response.json()["data"]
        assert "id" in response.json()["data"]["assignMedia"]
        assert "errors" not in response.json()
        assert response.json()["data"]["assignMedia"]["id"] == stage["id"]

    async def test_02_assign_media_stage_not_found(self, client):
        assets = get_session().query(AssetModel).filter(AssetModel.name == "test").all()
        response = await self.assign_media(client, 0, [asset.id for asset in assets])
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["message"] == "Stage not found"

    async def test_03_upload_media(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)

        variables = {
            "input": {
                "name": "test",
                "mediaType": "image",
                "filename": "test.png",
                "base64": f"data:image/jpeg;base64,{load_base64_from_image('src/assets/tests/images/test.png')}",
            }
        }

        query = """
            mutation uploadMedia($input: UploadMediaInput!) {
                uploadMedia(input: $input) {
                    id
                    }
                }
        """

        response = client.post(
            "/api/studio_graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )

        assert response.status_code == 200
        assert "data" in response.json()
        assert "uploadMedia" in response.json()["data"]
        assert "id" in response.json()["data"]["uploadMedia"]
        assert "errors" not in response.json()
        return response.json()["data"]["uploadMedia"]["id"]

    async def test_04_update_media(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        await test_AssetController.test_03_save_media_successfully(client)
        await self.test_03_upload_media(client)
        asset = newest_test_asset()
        original_file = asset.file_location
        file_location = "image/test2.png"
        response = self.update_media(client, headers, asset.id, file_location)
        self.remove_orphaned_upload(original_file)
        assert response.status_code == 200
        assert "data" in response.json()
        assert "updateMedia" in response.json()["data"]
        assert "id" in response.json()["data"]["updateMedia"]
        assert "errors" not in response.json()

        response = self.update_media(client, headers, 1000)
        assert response.status_code == 200
        assert "errors" in response.json()

        # Second-newest test asset: owned by a different faker user, so the
        # update must be refused (never the second row of the whole table).
        asset = (
            get_session()
            .query(AssetModel)
            .filter(AssetModel.name == "test")
            .order_by(AssetModel.id.desc())
            .offset(1)
            .first()
        )
        response = self.update_media(client, headers, asset.id, file_location)
        assert "errors" in response.json()

    @staticmethod
    def remove_orphaned_upload(file_location):
        """updateMedia moves the row to a new file_location; the file it was
        uploaded to is left behind, so delete it (the sweep only knows the
        row's current path)."""
        if not file_location:
            return
        path = os.path.join(UPLOAD_USER_CONTENT_FOLDER, file_location)
        if os.path.isfile(path):
            os.remove(path)

    def update_media(self, client, headers, id, file_location="image/test.png"):
        # updateMedia writes the uploaded frame under uploads/<type>/ with a
        # hashed name and, for a single frame, drops the reference again
        # (assets/services/asset.py), so nothing records the file. Diff the
        # directory around the request and delete what appeared.
        frames_dir = os.path.join(UPLOAD_USER_CONTENT_FOLDER, os.path.dirname(file_location))
        before = set(os.listdir(frames_dir)) if os.path.isdir(frames_dir) else set()
        try:
            return self._update_media(client, headers, id, file_location)
        finally:
            if os.path.isdir(frames_dir):
                for name in set(os.listdir(frames_dir)) - before:
                    path = os.path.join(frames_dir, name)
                    if os.path.isfile(path) and name != os.path.basename(file_location):
                        os.remove(path)

    def _update_media(self, client, headers, id, file_location):
        variables = {
            "input": {
                "id": id,
                "name": "updated_test",
                "mediaType": "image",
                "description": '{ "config": "test" }',
                "fileLocation": file_location,
                "base64": f"data:image/jpeg;base64,{load_base64_from_image('src/assets/tests/images/test.png')}",
                "copyrightLevel": 2,
                "playerAccess": "public",
                "uploadedFrames": [
                    f"data:image/jpeg;base64,{load_base64_from_image('src/assets/tests/images/test.png')}"
                ],
            }
        }

        query = """
            mutation updateMedia($input: UpdateMediaInput!) {
                updateMedia(input: $input) {
                    id
                    }
                }
        """

        response = client.post(
            "/api/studio_graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )
        return response

    async def test_05_delete_media(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        await self.test_03_upload_media(client)
        asset = newest_test_asset()
        original_file = asset.file_location
        self.update_media(client, headers, asset.id, f"image/test{random.randint(1, 1000)}.png")
        self.remove_orphaned_upload(original_file)

        response = self.delete_media_request(client, headers, asset)
        assert response.json()["data"]["deleteMediaOnStage"]["success"] is True

    async def test_06_delete_media_not_found(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        response = self.delete_media_request(client, headers, AssetModel(id=0))
        assert "errors" in response.json()
        assert response.json()["errors"][0]["message"] == "Media not found"

    def delete_media_request(self, client, headers, asset):
        variables = {"id": asset.id}

        query = """
            mutation deleteMediaOnStage($id: ID!) {
                deleteMediaOnStage(id: $id) {
                        success
                    }
                }
        """

        response = client.post(
            "/api/studio_graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )

        assert response.status_code == 200
        assert "data" in response.json()
        assert "deleteMediaOnStage" in response.json()["data"]
        return response

    async def assign_stages(self, client, headers, stage_ids, media_id):
        variables = {"input": {"stageIds": stage_ids, "id": media_id}}

        query = """
            mutation assignStages($input: AssignStagesInput!) {
                assignStages(input: $input) {
                        id
                    }
                }
        """

        response = client.post(
            "/api/studio_graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )
        return response

    async def test_07_assign_stages(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        stage = await test_StageController.test_01_create_stage(client)
        stage2 = await test_StageController.test_01_create_stage(client)
        await self.test_03_upload_media(client)
        asset = newest_test_asset()

        response = await self.assign_stages(client, headers, [stage["id"], stage2["id"]], asset.id)
        assert response.json()["data"]["assignStages"]["id"] is not None

    async def test_08_assign_media_round_trips_order(self, client):
        """assignMedia recreates the parent_stage rows in the order the client
        sent, and stage.assets must return them in that same order — it drives
        the media ordering in the on-stage toolbars (Stage Management > Media
        reorder feature)."""
        from upstage_backend.stages.db_models.stage import StageModel

        stage = await test_StageController.test_01_create_stage(client)
        session = get_session()

        # Ensure at least two assets so a reversed order is distinguishable.
        await self.test_03_upload_media(client)
        template = newest_test_asset()
        extra = AssetModel(
            name="reorder extra",
            asset_type_id=template.asset_type_id,
            owner_id=template.owner_id,
            file_location=f"test/reorder-extra-{random.randint(0, 10**9)}.png",
            size=1,
        )
        session.add(extra)
        session.commit()

        ids = [asset.id for asset in session.query(AssetModel).order_by(AssetModel.id).all()]
        assert len(ids) >= 2
        reordered = list(reversed(ids))

        response = await self.assign_media(client, stage["id"], reordered)
        assert "errors" not in response.json()

        stage_row = session.query(StageModel).filter_by(id=stage["id"]).first()
        assert [row.child_asset_id for row in stage_row.assets] == reordered
