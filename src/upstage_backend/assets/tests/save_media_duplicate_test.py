# -*- coding: iso8859-15 -*-
"""
Regression tests for save_media's duplicate-stream-key handling.

Previously the new AssetModel was session.add()ed before
process_file_location() validated key uniqueness; the GraphQLError response
is HTTP 200, so the db_request_session middleware committed the pending
half-built row and crashed with a NOT NULL violation on file_location.
After the reorder, a duplicate-key rejection must leave no pending asset:
no orphan rows, and the same client must be able to keep saving media.
"""

import time

import pytest
from sqlalchemy import text

from upstage_backend.authentication.tests.auth_test import TestAuthenticationController
from upstage_backend.global_config.env import JWT_HEADER_NAME

test_AuthenticationController = TestAuthenticationController()

DUPLICATE_KEY = "savemediaduptestkey"


@pytest.mark.anyio
class TestSaveMediaDuplicateKey:
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

    def _save(self, client, headers, name, key):
        return client.post(
            "/api/studio_graphql",
            json={
                "query": self.save_media_query,
                "variables": {
                    "input": {
                        "name": name,
                        "mediaType": "stream",
                        "owner": "",
                        "urls": [key],
                        "copyrightLevel": 0,
                        "stageAssignments": [],
                        "userIds": [],
                        "tags": [],
                        "w": 16,
                        "h": 9,
                    }
                },
            },
            headers=headers,
        )

    def _asset_count(self, db_engine):
        with db_engine.connect() as connection:
            return connection.execute(text("SELECT count(*) FROM asset")).scalar_one()

    async def test_01_duplicate_key_rejected_without_orphan_row(self, client, db_engine):
        headers = await self._headers(client)

        # Ensure the key exists (idempotent across runs against the dev DB).
        with db_engine.connect() as connection:
            existing = connection.execute(
                text("SELECT id FROM asset WHERE file_location = :key"),
                {"key": DUPLICATE_KEY},
            ).first()
        if not existing:
            response = self._save(client, headers, "dup-key original", DUPLICATE_KEY)
            assert response.status_code == 200, response.text
            assert response.json().get("errors") is None, response.json()

        count_before = self._asset_count(db_engine)

        response = self._save(client, headers, "dup-key attempt", DUPLICATE_KEY)
        # saveMedia's payload type is non-null, so the field error nulls the
        # whole `data` and Ariadne's HTTP handler maps that to 400 (its
        # standard behavior; unrelated to the session-reorder fix).
        assert response.status_code == 400, response.text
        body = response.json()
        assert body.get("errors"), body
        assert "already existed" in body["errors"][0]["message"], body

        # The rejected save must leave nothing behind: same row count, and
        # in particular no half-built row (a NULL file_location insert used
        # to crash the post-response commit before the reorder).
        assert self._asset_count(db_engine) == count_before
        with db_engine.connect() as connection:
            null_rows = connection.execute(
                text("SELECT count(*) FROM asset WHERE file_location IS NULL")
            ).scalar_one()
        assert null_rows == 0

    async def test_02_session_still_usable_after_rejection(self, client, db_engine):
        headers = await self._headers(client)

        rejected = self._save(client, headers, "dup-key attempt 2", DUPLICATE_KEY)
        assert rejected.json().get("errors"), rejected.json()

        fresh_key = f"savemediafresh{int(time.time())}"
        response = self._save(client, headers, "fresh key after rejection", fresh_key)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body.get("errors") is None, body
        assert body["data"]["saveMedia"]["asset"]["id"]

        with db_engine.connect() as connection:
            row = connection.execute(
                text("SELECT file_location FROM asset WHERE file_location = :key"),
                {"key": fresh_key},
            ).first()
        assert row is not None
