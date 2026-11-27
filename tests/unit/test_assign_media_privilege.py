"""Stage Management > Media may only ADD media the stage owner is allowed to
use; items already on the stage (put there by their owner, say) survive a
re-save. Admins are exempt."""

from __future__ import annotations

import pytest
from graphql import GraphQLError

from upstage_backend.assets.db_models.asset import AssetModel, Previlege
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.services.media import MediaService
from upstage_backend.users.db_models.user import ADMIN, PLAYER


class _User:
    def __init__(self, id, role=PLAYER):
        self.id = id
        self.role = role


class _Asset:
    def __init__(self, id, owner_id, name):
        self.id = id
        self.owner_id = owner_id
        self.name = name


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    """select(ParentStageModel.child_asset_id) → the current assignment ids;
    select(AssetModel) → the asset rows whose ids were asked for."""

    def __init__(self, existing_ids, assets):
        self.existing_ids = existing_ids
        self.assets = assets

    def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is ParentStageModel:
            return _Result(list(self.existing_ids))
        assert entity is AssetModel
        wanted = set(statement.whereclause.right.value)
        return _Result([a for a in self.assets if a.id in wanted])


@pytest.fixture
def service(monkeypatch):
    service = MediaService()
    privileges = {}
    monkeypatch.setattr(
        service.asset_service,
        "resolve_privilege",
        lambda user_id, asset, usages=None: privileges.get(
            asset.id, Previlege.REQUIRE_APPROVAL.value
        ),
    )
    service._privileges = privileges
    return service


def test_new_media_without_usage_right_is_refused(service):
    session = _Session(existing_ids=[1], assets=[_Asset(2, owner_id=9, name="Locked")])
    with pytest.raises(GraphQLError, match="Locked"):
        service.assert_may_use_new_media(session, _User(5), stage_id=3, media_ids=[1, 2])


def test_existing_assignments_own_and_approved_media_pass(service):
    session = _Session(
        existing_ids=[1],
        assets=[_Asset(1, 9, "AlreadyThere"), _Asset(2, 5, "Mine"), _Asset(4, 9, "Granted")],
    )
    service._privileges[4] = Previlege.APPROVED.value
    service.assert_may_use_new_media(session, _User(5), stage_id=3, media_ids=[1, 2, 4])


def test_admin_is_exempt(service):
    session = _Session(existing_ids=[], assets=[_Asset(2, 9, "Locked")])
    service.assert_may_use_new_media(session, _User(5, ADMIN), stage_id=3, media_ids=[2])
