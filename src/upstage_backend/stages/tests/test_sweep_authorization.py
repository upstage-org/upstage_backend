# -*- coding: iso8859-15 -*-
"""
sweepStage archives a stage's live events and clears it — it ends whatever is
on that stage. It was callable by ANY logged-in player account: the resolver
checks the account role, but the service never checked the caller's
permission on the stage being swept, unlike every sibling mutation
(update/delete/status/... all go through extract_permission).

Rule (2026-09): audience sessions watch, chat and react — nothing else. An
account that is only audience on a stage, or a plain performer on it, must
not be able to sweep it; the Stage Management panel that offers the button is
already limited to owner / editor / admin.
"""

import pytest
from upstage_backend.authentication.tests.auth_test import (
    TestAuthenticationController as _TestAuthenticationController,
)
from upstage_backend.stages.tests.test_stage import TestStageController as _TestStageController
from upstage_backend.users.db_models.user import PLAYER, SUPER_ADMIN

test_AuthenticationController = _TestAuthenticationController()
test_StageController = _TestStageController()

SWEEP = """
    mutation sweepStage($id: ID!) {
        sweepStage(id: $id) { success performanceId }
    }
"""


def _sweep(client, headers, stage_id):
    return client.post(
        "/api/studio_graphql",
        json={"query": SWEEP, "variables": {"id": stage_id}},
        headers=headers,
    ).json()


@pytest.mark.anyio
class TestSweepAuthorization:
    async def test_01_an_unrelated_player_account_cannot_sweep_a_stage(self, client):
        stage = await test_StageController.test_01_create_stage(client)
        outsider = test_AuthenticationController.get_headers(client, PLAYER)

        data = _sweep(client, outsider, stage["id"])

        assert data["errors"][0]["message"] == "You are not authorized to update this stage"

    async def test_02_an_anonymous_session_cannot_sweep_a_stage(self, client):
        stage = await test_StageController.test_01_create_stage(client)

        data = _sweep(client, {}, stage["id"])

        assert "errors" in data
        assert not (data.get("data") or {}).get("sweepStage")

    async def test_03_an_admin_still_reaches_the_sweep(self, client):
        stage = await test_StageController.test_01_create_stage(client)
        admin = test_AuthenticationController.get_headers(client, SUPER_ADMIN)

        data = _sweep(client, admin, stage["id"])

        # Authorised: the request gets as far as the sweep itself (a freshly
        # created stage has no live events, hence this message).
        messages = [e["message"] for e in data.get("errors", [])]
        assert "You are not authorized to update this stage" not in messages
        assert (data.get("data") or {}).get("sweepStage") or messages == [
            "The stage is already sweeped!"
        ]

    async def test_04_a_missing_stage_is_reported_as_such(self, client):
        admin = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        data = _sweep(client, admin, 0)
        assert data["errors"][0]["message"] == "Stage not found"
