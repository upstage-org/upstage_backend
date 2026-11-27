from sqlalchemy import select
import pytest
from upstage_backend.assets.tests.asset_test import (
    TestAssetController as _TestAssetController,
    newest_test_asset,
)
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
from upstage_backend.authentication.tests.auth_test import (
    TestAuthenticationController as _TestAuthenticationController,
)
from upstage_backend.global_config import get_session
from upstage_backend.users.db_models.user import PLAYER, SUPER_ADMIN

test_AssetController = _TestAssetController()
test_AuthenticationController = _TestAuthenticationController()


@pytest.mark.anyio
class TestLicenseController:
    async def test_00_license_mutations_require_admin(self, client):
        """createLicense / revokeLicense used to be open to anyone."""
        query = """
            mutation($id: ID!) {
                revokeLicense(id: $id)
            }
        """
        anonymous = client.post(
            "/api/studio_graphql", json={"query": query, "variables": {"id": 1}}
        )
        assert anonymous.json()["errors"][0]["message"] == "Authenticated Failed"

        player_headers = test_AuthenticationController.get_headers(client, PLAYER)
        as_player = client.post(
            "/api/studio_graphql",
            json={"query": query, "variables": {"id": 1}},
            headers=player_headers,
        )
        assert as_player.json()["errors"][0]["message"] == "Permission denied"

    async def test_01_create_license(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
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
            "/api/studio_graphql", json={"query": query, "variables": variables}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["createLicense"]["assetId"] == str(asset.id)
        assert response.json()["data"]["createLicense"]["level"] == 1
        assert response.json()["data"]["createLicense"]["permissions"] == "{}"
        assert response.json()["data"]["createLicense"]["assetPath"] is not None

    async def test_02_revoke_license(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        # The license test_01 created on the newest test asset - never the
        # first license row of a shared database.
        asset = newest_test_asset()
        license = (
            get_session()
            .scalars(
                select(AssetLicenseModel)
                .filter_by(asset_id=asset.id)
                .order_by(AssetLicenseModel.id.desc())
                .limit(1)
            )
            .first()
        )
        query = """
            mutation($id: ID!) {
                revokeLicense(id: $id)
            }
        """

        variables = {"id": license.id}

        response = client.post(
            "/api/studio_graphql", json={"query": query, "variables": variables}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["revokeLicense"] == "License revoked {}".format(license.id)

        response = client.post(
            "/api/studio_graphql", json={"query": query, "variables": variables}, headers=headers
        )
        # Already gone: the service reports it as a GraphQL error.
        assert response.json()["errors"][0]["message"] == "License not found"
        license = (
            get_session()
            .scalars(select(AssetLicenseModel).filter_by(id=license.id).limit(1))
            .first()
        )
        assert license is None
