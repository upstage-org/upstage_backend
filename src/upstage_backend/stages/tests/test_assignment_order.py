# -*- coding: iso8859-15 -*-
"""
A stage's saved media order IS the parent_stage primary-key order (assignMedia
writes the rows in the order arranged in Stage Management > Media, and
StageModel.assets reads them back ORDER BY id).

Every per-media mutation (assignStages, quickAssignMutation, saveMedia) used
to delete ALL of that media item's parent_stage rows and insert fresh ones.
Fresh rows get fresh, higher ids — so merely re-saving a media item (renaming
a stream feed, ticking another stage in the media form, ...) silently moved
it to the END of the order on every stage it was already assigned to, undoing
the arrangement the stage owner had saved. Reported 2026-09 as "reorder media
tool not working properly".

These tests pin the rule: an assignment that survives a media save keeps its
row (and so its position); only genuinely new assignments go to the end.
"""

import random

import pytest
from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.assets.tests.asset_test import newest_test_asset
from upstage_backend.authentication.tests.auth_test import (
    TestAuthenticationController as _TestAuthenticationController,
)
from upstage_backend.global_config import get_session
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.tests.test_media import TestMediaController as _TestMediaController
from upstage_backend.stages.tests.test_stage import TestStageController as _TestStageController
from upstage_backend.users.db_models.user import SUPER_ADMIN

test_AuthenticationController = _TestAuthenticationController()
test_StageController = _TestStageController()
test_MediaController = _TestMediaController()


def _stage_order(stage_id):
    session = get_session()
    session.expire_all()
    stage_row = session.query(StageModel).filter_by(id=stage_id).first()
    return [row.child_asset_id for row in stage_row.assets]


def _rows(stage_id, asset_id):
    session = get_session()
    session.expire_all()
    return (
        session.query(ParentStageModel)
        .filter_by(stage_id=int(stage_id), child_asset_id=int(asset_id))
        .order_by(ParentStageModel.id)
        .all()
    )


@pytest.mark.anyio
class TestAssignmentOrder:
    async def _stage_with_three_assets(self, client):
        """A stage whose saved order is [a, b, c]."""
        stage = await test_StageController.test_01_create_stage(client)
        await test_MediaController.test_03_upload_media(client)
        template = newest_test_asset()
        session = get_session()
        assets = []
        for label in ("a", "b", "c"):
            asset = AssetModel(
                name=f"order {label}",
                asset_type_id=template.asset_type_id,
                owner_id=template.owner_id,
                file_location=f"test/order-{label}-{random.randint(0, 10**9)}.png",
                size=1,
            )
            session.add(asset)
            assets.append(asset)
        session.commit()
        ids = [asset.id for asset in assets]
        response = await test_MediaController.assign_media(client, stage["id"], ids)
        assert "errors" not in response.json()
        assert _stage_order(stage["id"]) == ids
        return stage, ids

    async def test_01_assign_stages_keeps_the_items_position(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        stage, (a, b, c) = await self._stage_with_three_assets(client)
        other = await test_StageController.test_01_create_stage(client)

        # Media form: "a" stays on `stage` and is additionally put on `other`.
        response = await test_MediaController.assign_stages(
            client, headers, [stage["id"], other["id"]], a
        )
        assert "errors" not in response.json()

        assert _stage_order(stage["id"]) == [a, b, c]
        assert _stage_order(other["id"]) == [a]

    async def test_02_assign_stages_removes_and_adds(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        stage, (a, b, c) = await self._stage_with_three_assets(client)
        other = await test_StageController.test_01_create_stage(client)

        # Move "b" from `stage` to `other`.
        response = await test_MediaController.assign_stages(client, headers, [other["id"]], b)
        assert "errors" not in response.json()
        assert _stage_order(stage["id"]) == [a, c]
        assert _stage_order(other["id"]) == [b]

        # Put it back: a NEW assignment goes to the end of that stage.
        response = await test_MediaController.assign_stages(
            client, headers, [other["id"], stage["id"]], b
        )
        assert "errors" not in response.json()
        assert _stage_order(stage["id"]) == [a, c, b]

    async def test_03_quick_assign_keeps_the_items_position(self, client):
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        stage, (a, b, c) = await self._stage_with_three_assets(client)
        other = await test_StageController.test_01_create_stage(client)

        query = """
            mutation quickAssign($assetId: ID!, $stageIds: [ID]!) {
                quickAssignMutation(assetId: $assetId, stageIds: $stageIds) { success }
            }
        """
        response = client.post(
            "/api/studio_graphql",
            json={
                "query": query,
                "variables": {"assetId": a, "stageIds": [other["id"], stage["id"]]},
            },
            headers=headers,
        )
        assert "errors" not in response.json()
        assert _stage_order(stage["id"]) == [a, b, c]
        assert _stage_order(other["id"]) == [a]

    async def test_04_sync_keeps_rows_and_exit_settings(self, client):
        """Service-level: surviving rows keep their id; explicit exit values
        win, missing ones keep what the row had (same rule as before)."""
        from upstage_backend.stages.services.assignment import sync_asset_assignments

        stage, (a, b, c) = await self._stage_with_three_assets(client)
        session = get_session()
        row = _rows(stage["id"], a)[0]
        row.exit_animation = "fade"
        row.exit_speed = 1500
        session.commit()
        row_id = row.id

        sync_asset_assignments(session, a, [(stage["id"], None, 2500)])
        session.commit()

        rows = _rows(stage["id"], a)
        assert [r.id for r in rows] == [row_id]
        assert rows[0].exit_animation == "fade"
        assert rows[0].exit_speed == 2500
        assert _stage_order(stage["id"]) == [a, b, c]

    async def test_05_sync_collapses_duplicates_and_repeated_stage_ids(self, client):
        """parent_stage has no unique constraint: two racing saves can leave
        the same (stage, asset) pair twice. A save must heal that, keeping
        the EARLIEST row (the item's saved position), and must not create
        duplicates when the client repeats a stage id."""
        from upstage_backend.stages.services.assignment import sync_asset_assignments

        stage, (a, b, c) = await self._stage_with_three_assets(client)
        session = get_session()
        session.add(ParentStageModel(stage_id=int(stage["id"]), child_asset_id=a))
        session.commit()
        assert _stage_order(stage["id"]) == [a, b, c, a]

        sync_asset_assignments(session, a, [(stage["id"], None, None), (stage["id"], None, None)])
        session.commit()
        assert _stage_order(stage["id"]) == [a, b, c]

    async def test_06_sync_with_nothing_wanted_unassigns_everywhere(self, client):
        from upstage_backend.stages.services.assignment import sync_asset_assignments

        stage, (a, b, c) = await self._stage_with_three_assets(client)
        session = get_session()
        sync_asset_assignments(session, b, [])
        session.commit()
        assert _stage_order(stage["id"]) == [a, c]

    async def test_07_save_media_keeps_the_items_position_and_exit_settings(self, client):
        """The media form's Save (saveMedia) on an item that is already on the
        stage: position kept, an explicit exit animation applied, and a newly
        ticked stage appended."""
        headers = test_AuthenticationController.get_headers(client, SUPER_ADMIN)
        stage, (a, b, c) = await self._stage_with_three_assets(client)
        other = await test_StageController.test_01_create_stage(client)
        session = get_session()
        asset = session.query(AssetModel).filter_by(id=a).first()
        row_id = _rows(stage["id"], a)[0].id

        mutation_query = """
            mutation SaveMedia($input: SaveMediaInput!) {
                saveMedia(input: $input) { asset { id } }
            }
        """
        variables = {
            "input": {
                "id": a,
                "name": "order a renamed",
                "mediaType": asset.asset_type.name,
                "urls": [asset.file_location],
                "w": 100,
                "h": 100,
                "copyrightLevel": 0,
                "owner": asset.owner.username,
                "tags": [],
                "userIds": [],
                "stageAssignments": [
                    {"stageId": stage["id"], "exitAnimation": "fade", "exitSpeed": 1200},
                    {"stageId": other["id"]},
                ],
            }
        }
        response = client.post(
            "/api/studio_graphql",
            json={"query": mutation_query, "variables": variables},
            headers=headers,
        )
        assert "errors" not in response.json(), response.json()

        assert _stage_order(stage["id"]) == [a, b, c]
        assert _stage_order(other["id"]) == [a]
        rows = _rows(stage["id"], a)
        assert [r.id for r in rows] == [row_id]
        assert (rows[0].exit_animation, rows[0].exit_speed) == ("fade", 1200)
