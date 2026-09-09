# -*- coding: iso8859-15 -*-


import pytest
from upstage_backend.assets.tests.asset_test import TestAssetController as _TestAssetController, newest_test_asset
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
from upstage_backend.global_config import get_session

test_AssetController = _TestAssetController()


@pytest.mark.anyio
class TestLicenseController:
    async def test_01_create_license(self, client):
        await test_AssetController.test_03_save_media_successfully(client)
        asset = newest_test_asset()
        query = """
        mutation ($input: LicenseInput!) {
          createLicense(input: $input) {
            assetId
            level
            permissions
            assetPath
          }
        }
        """
        variables = {
            "input": {
                "assetId": asset.id,
                "level": 1,
                "permissions": "{}",
            }
        }

        response = client.post(
            "/api/studio_graphql", json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        assert response.json()["data"]["createLicense"]["assetId"] == str(asset.id)
        assert response.json()["data"]["createLicense"]["level"] == 1
        assert response.json()["data"]["createLicense"]["permissions"] == "{}"
        assert response.json()["data"]["createLicense"]["assetPath"] is not None

    async def test_02_revoke_license(self, client):
        # The license test_01 created on the newest test asset - never the
        # first license row of a shared database.
        asset = newest_test_asset()
        license = (
            get_session()
            .query(AssetLicenseModel)
            .filter_by(asset_id=asset.id)
            .order_by(AssetLicenseModel.id.desc())
            .first()
        )
        query = """
            mutation($id: ID!) {
                revokeLicense(id: $id)
            }
        """

        variables = {"id": license.id}

        response = client.post(
            "/api/studio_graphql", json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        assert response.json()["data"]["revokeLicense"] == "License revoked {}".format(
            license.id
        )

        response = client.post(
            "/api/studio_graphql", json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        assert response.json()["data"][
            "revokeLicense"
        ] == "Failed to revoke license {}".format(license.id)
        license = (
            get_session().query(AssetLicenseModel).filter_by(id=license.id).first()
        )
        assert license is None
