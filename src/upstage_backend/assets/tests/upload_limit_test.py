# -*- coding: iso8859-15 -*-
"""
Upload limits end-to-end through the GraphQL API (real DB; runs inside the
compose network, e.g. the disposable e2e backend with
UPSTAGE_TESTS_ALLOW_REAL_DB=1).

Scenarios (2026-09-05 report):
  * admin / super admin: uploads above 1 MB succeed; whoami reports the
    server-wide 500 MiB maximum (nginx client_max_body_size is 500M too)
  * player, no change: default 1 MiB, a 1.2 MB file is refused
  * player, limit raised by an admin to 2 MiB: the same file is accepted
  * player, limit put back to 1 MiB: the same file is refused again
"""

import base64
import os

import pytest
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController
from upstage_backend.global_config.env import UPLOAD_USER_CONTENT_FOLDER as storagePath
from upstage_backend.users.db_models.user import ADMIN, PLAYER, SUPER_ADMIN

test_AuthenticationController = TestAuthenticationController()

MIB = 1024 * 1024
ONE_POINT_TWO_MB = int(1.2 * MIB)
SERVER_MAX = 500 * MIB

UPLOAD = """
    mutation UploadFile($base64: String!, $filename: String!) {
        uploadFile(base64: $base64, filename: $filename) { url }
    }
"""
WHOAMI = "query { whoami { id username email role active uploadLimit effectiveUploadLimit } }"
CURRENT_USER = "query { currentUser { id uploadLimit effectiveUploadLimit } }"
UPDATE_USER = """
    mutation UpdateUser($input: UpdateUserInput!) {
        updateUser(input: $input) { id uploadLimit }
    }
"""


def _png_payload(size: int) -> str:
    # The upload path only measures decoded bytes and writes them; content
    # is never image-validated, so a deterministic blob is enough.
    return "data:image/png;base64," + base64.b64encode(b"\x89PNG" + b"\0" * (size - 4)).decode()


def _post(client, headers, query, variables=None):
    response = client.post(
        "/api/studio_graphql", headers=headers, json={"query": query, "variables": variables or {}}
    )
    # The backend answers GraphQL-level errors (e.g. an over-limit upload)
    # with HTTP 400 and the usual {"errors": [...]} body; both are "ok" here,
    # the assertions below look at the body.
    assert response.status_code in (200, 400), response.text
    return response.json()


def _whoami(client, headers):
    body = _post(client, headers, WHOAMI)
    assert "errors" not in body, body
    return body["data"]["whoami"]


def _upload(client, headers, size, filename="frame.png"):
    return _post(client, headers, UPLOAD, {"base64": _png_payload(size), "filename": filename})


def _set_limit(client, admin_headers, player, limit):
    body = _post(
        client,
        admin_headers,
        UPDATE_USER,
        {
            "input": {
                "id": int(player["id"]),
                "username": player["username"],
                "email": player["email"],
                "role": int(player["role"]),
                "active": player["active"],
                "uploadLimit": limit,
            }
        },
    )
    assert "errors" not in body, body
    assert body["data"]["updateUser"]["uploadLimit"] == limit


@pytest.fixture
def uploaded_files():
    """Best-effort removal of the blobs the tests write under storagePath."""
    urls = []
    yield urls
    for url in urls:
        try:
            os.remove(os.path.join(storagePath, url))
        except OSError:
            pass


@pytest.mark.anyio
class TestUploadLimits:
    @pytest.mark.parametrize("role", [SUPER_ADMIN, ADMIN])
    async def test_admin_uploads_above_1mb(self, client, uploaded_files, role):
        headers = test_AuthenticationController.get_headers(client, role)

        me = _whoami(client, headers)
        assert me["uploadLimit"] == MIB, "stored per-user value is untouched (column default)"
        assert me["effectiveUploadLimit"] == SERVER_MAX
        assert _post(client, headers, CURRENT_USER)["data"]["currentUser"][
            "effectiveUploadLimit"
        ] == SERVER_MAX

        body = _upload(client, headers, ONE_POINT_TWO_MB)
        assert "errors" not in body, body
        assert body["data"]["uploadFile"]["url"]
        uploaded_files.append(body["data"]["uploadFile"]["url"])

    async def test_player_default_then_increase_then_decrease(self, client, uploaded_files):
        admin_headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        player_headers = test_AuthenticationController.get_headers(client, PLAYER)

        # No change: default 1 MiB.
        player = _whoami(client, player_headers)
        assert player["uploadLimit"] == MIB
        assert player["effectiveUploadLimit"] == MIB
        body = _upload(client, player_headers, ONE_POINT_TWO_MB)
        assert body["errors"][0]["message"] == "File size must be under 1MB."
        body = _upload(client, player_headers, 900 * 1024)
        assert "errors" not in body, body
        uploaded_files.append(body["data"]["uploadFile"]["url"])

        # Admin raises the limit to 2 MiB: the 1.2 MB file now goes through.
        _set_limit(client, admin_headers, player, 2 * MIB)
        assert _whoami(client, player_headers)["effectiveUploadLimit"] == 2 * MIB
        body = _upload(client, player_headers, ONE_POINT_TWO_MB)
        assert "errors" not in body, body
        uploaded_files.append(body["data"]["uploadFile"]["url"])

        # Admin puts it back to 1 MiB: refused again.
        _set_limit(client, admin_headers, player, MIB)
        assert _whoami(client, player_headers)["effectiveUploadLimit"] == MIB
        body = _upload(client, player_headers, ONE_POINT_TWO_MB)
        assert body["errors"][0]["message"] == "File size must be under 1MB."

    async def test_update_user_without_upload_limit_keeps_stored_value(self, client):
        admin_headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        player_headers = test_AuthenticationController.get_headers(client, PLAYER)
        player = _whoami(client, player_headers)

        body = _post(
            client,
            admin_headers,
            UPDATE_USER,
            {
                "input": {
                    "id": int(player["id"]),
                    "username": player["username"],
                    "email": player["email"],
                    "role": int(player["role"]),
                    "active": player["active"],
                    "displayName": "Renamed",
                }
            },
        )
        assert "errors" not in body, body
        assert body["data"]["updateUser"]["uploadLimit"] == MIB
