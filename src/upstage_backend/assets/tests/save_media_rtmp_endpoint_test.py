# -*- coding: iso8859-15 -*-
"""
Multi-server streaming: saveMedia accepts an optional `rtmpEndpoint` for RTMP
stream feeds and stores it (normalised) in the asset description next to
`isRTMP`. Omitted ⇒ nothing is written (legacy behaviour); malformed ⇒ the
mutation is rejected and no asset row is left behind.
"""

import json
import time

import pytest
from sqlalchemy import text

from upstage_backend.assets.services.asset import normalise_rtmp_endpoint
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController as _TestAuthenticationController
from upstage_backend.global_config.env import JWT_HEADER_NAME

test_AuthenticationController = _TestAuthenticationController()


def test_normalise_rtmp_endpoint_accepts_origins():
    assert normalise_rtmp_endpoint("https://streaming4.upstage.live") == (
        "https://streaming4.upstage.live"
    )
    assert normalise_rtmp_endpoint(" https://streaming4.upstage.live/ ") == (
        "https://streaming4.upstage.live"
    )
    assert normalise_rtmp_endpoint("http://localhost:8989") == "http://localhost:8989"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "streaming4.upstage.live",
        "rtmp://streaming4.upstage.live/live",
        "https://streaming4.upstage.live/live",
        "https://streaming4.upstage.live?x=1",
        "https://user:pw@streaming4.upstage.live",
        "javascript:alert(1)",
    ],
)
def test_normalise_rtmp_endpoint_rejects_junk(bad):
    from graphql import GraphQLError

    with pytest.raises(GraphQLError):
        normalise_rtmp_endpoint(bad)


@pytest.mark.anyio
class TestSaveMediaRtmpEndpoint:
    save_media_query = """
        mutation SaveMedia($input: SaveMediaInput!) {
            saveMedia(input: $input) {
                asset {
                    id
                }
            }
        }
    """

    async def _headers(self, client):
        data = await test_AuthenticationController.test_02_login_successfully(client)
        return {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }

    def _save(self, client, headers, name, key, media_type="stream", **extra):
        payload = {
            "name": name,
            "mediaType": media_type,
            "owner": "",
            "urls": [key],
            "copyrightLevel": 0,
            "stageAssignments": [],
            "userIds": [],
            "tags": [],
            "w": 16,
            "h": 9,
        }
        payload.update(extra)
        return client.post(
            "/api/studio_graphql",
            json={"query": self.save_media_query, "variables": {"input": payload}},
            headers=headers,
        )

    def _description(self, db_engine, key):
        with db_engine.connect() as connection:
            row = connection.execute(
                text("SELECT description FROM asset WHERE file_location = :key"),
                {"key": key},
            ).first()
        assert row is not None, f"asset {key} not found"
        return json.loads(row[0] or "{}")

    def _asset_count(self, db_engine):
        with db_engine.connect() as connection:
            return connection.execute(text("SELECT count(*) FROM asset")).scalar_one()

    async def test_01_stores_normalised_endpoint(self, client, db_engine):
        headers = await self._headers(client)
        key = f"rtmpep{int(time.time())}a"
        response = self._save(
            client,
            headers,
            "bound feed",
            key,
            rtmpEndpoint="https://streaming4.upstage.live/",
        )
        assert response.status_code == 200, response.text
        assert response.json().get("errors") is None, response.json()
        meta = self._description(db_engine, key)
        assert meta["isRTMP"] is True
        assert meta["rtmpEndpoint"] == "https://streaming4.upstage.live"

    async def test_02_omitted_endpoint_writes_nothing(self, client, db_engine):
        headers = await self._headers(client)
        key = f"rtmpep{int(time.time())}b"
        response = self._save(client, headers, "legacy feed", key)
        assert response.status_code == 200, response.text
        assert response.json().get("errors") is None, response.json()
        meta = self._description(db_engine, key)
        assert meta["isRTMP"] is True
        assert "rtmpEndpoint" not in meta

    async def test_03_malformed_endpoint_rejected_without_row(self, client, db_engine):
        headers = await self._headers(client)
        key = f"rtmpep{int(time.time())}c"
        count_before = self._asset_count(db_engine)
        response = self._save(
            client,
            headers,
            "bad feed",
            key,
            rtmpEndpoint="https://streaming4.upstage.live/live",
        )
        body = response.json()
        assert body.get("errors"), body
        assert "Invalid streaming server" in body["errors"][0]["message"], body
        assert self._asset_count(db_engine) == count_before
