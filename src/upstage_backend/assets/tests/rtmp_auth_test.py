# -*- coding: iso8859-15 -*-
"""
Tests for the MediaMTX publish-auth endpoint (/api/rtmp/auth).

Token contract mirrors AssetService.resolve_sign():
    "<ts>-<md5('/live/<key>-<ts>-<STREAM_KEY>')>"
"""

import hashlib
import time

import pytest

from upstage_backend.assets.http import rtmp_auth
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController
from upstage_backend.global_config.env import JWT_HEADER_NAME

test_AuthenticationController = TestAuthenticationController()

STREAM_ASSET_KEY = "rtmpauthtestkey"


def make_token(key: str, ts: int, stream_key: str) -> str:
    digest = hashlib.md5(f"/live/{key}-{ts}-{stream_key}".encode("utf-8")).hexdigest()
    return f"{ts}-{digest}"


def auth_payload(**overrides):
    payload = {
        "user": "",
        "password": "",
        "ip": "172.17.0.1",
        "action": "publish",
        "path": f"live/{STREAM_ASSET_KEY}",
        "protocol": "rtmp",
        "id": "test-conn",
        "query": "",
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
class TestRtmpAuth:
    save_media_query = """
        mutation SaveMedia($input: SaveMediaInput!) {
            saveMedia(input: $input) {
                asset {
                    id
                }
            }
        }
    """

    async def _create_stream_asset(self, client, db_engine):
        from sqlalchemy import text

        # The asset persists across test runs against a shared dev DB, and
        # saveMedia's duplicate-key rejection leaves a half-added row in the
        # request session (pre-existing wart) — so skip creation if present.
        with db_engine.connect() as connection:
            existing = connection.execute(
                text("SELECT id FROM asset WHERE file_location = :key"),
                {"key": STREAM_ASSET_KEY},
            ).first()
        if existing:
            return

        data = await test_AuthenticationController.test_02_login_successfully(client)
        headers = {
            "Authorization": f"Bearer {data['data']['login']['access_token']}",
            JWT_HEADER_NAME: data["data"]["login"]["refresh_token"],
        }
        response = client.post(
            "/api/studio_graphql",
            json={
                "query": self.save_media_query,
                "variables": {
                    "input": {
                        "name": "RTMP auth test stream",
                        "mediaType": "stream",
                        "owner": "",
                        "urls": [STREAM_ASSET_KEY],
                        "copyrightLevel": 0,
                        "stageIds": [],
                        "userIds": [],
                        "tags": [],
                        "w": 16,
                        "h": 9,
                    }
                },
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body.get("errors") is None, body
        assert body["data"]["saveMedia"]["asset"]["id"]

    async def test_01_valid_token_accepted(self, client, db_engine):
        await self._create_stream_asset(client, db_engine)
        ts = int(time.time()) + 3600
        token = make_token(STREAM_ASSET_KEY, ts, rtmp_auth.STREAM_KEY)
        response = client.post("/api/rtmp/auth", json=auth_payload(query=f"token={token}"))
        assert response.status_code == 204, response.text

    async def test_02_token_in_password_slot_accepted(self, client):
        ts = int(time.time()) + 3600
        token = make_token(STREAM_ASSET_KEY, ts, rtmp_auth.STREAM_KEY)
        response = client.post("/api/rtmp/auth", json=auth_payload(password=token))
        assert response.status_code == 204, response.text

    async def test_03_expired_token_rejected(self, client):
        ts = int(time.time()) - 10
        token = make_token(STREAM_ASSET_KEY, ts, rtmp_auth.STREAM_KEY)
        response = client.post("/api/rtmp/auth", json=auth_payload(query=f"token={token}"))
        assert response.status_code == 401

    async def test_04_bad_digest_rejected(self, client):
        ts = int(time.time()) + 3600
        token = f"{ts}-{'0' * 32}"
        response = client.post("/api/rtmp/auth", json=auth_payload(query=f"token={token}"))
        assert response.status_code == 401

    async def test_05_missing_token_rejected(self, client):
        response = client.post("/api/rtmp/auth", json=auth_payload())
        assert response.status_code == 401

    async def test_06_unknown_stream_key_rejected(self, client):
        key = "nosuchstreamkey"
        ts = int(time.time()) + 3600
        token = make_token(key, ts, rtmp_auth.STREAM_KEY)
        response = client.post(
            "/api/rtmp/auth",
            json=auth_payload(path=f"live/{key}", query=f"token={token}"),
        )
        assert response.status_code == 401

    async def test_07_non_live_path_rejected(self, client):
        ts = int(time.time()) + 3600
        token = make_token(STREAM_ASSET_KEY, ts, rtmp_auth.STREAM_KEY)
        response = client.post(
            "/api/rtmp/auth",
            json=auth_payload(path=f"other/{STREAM_ASSET_KEY}", query=f"token={token}"),
        )
        assert response.status_code == 401

    async def test_08_read_action_allowed_without_token(self, client):
        response = client.post("/api/rtmp/auth", json=auth_payload(action="read"))
        assert response.status_code == 204

    async def test_09_empty_stream_key_fails_closed(self, client, monkeypatch):
        monkeypatch.setattr(rtmp_auth, "STREAM_KEY", "")
        ts = int(time.time()) + 3600
        token = make_token(STREAM_ASSET_KEY, ts, "")
        response = client.post("/api/rtmp/auth", json=auth_payload(query=f"token={token}"))
        assert response.status_code == 503
