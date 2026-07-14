"""Per-stage-assignment exit-animation persistence.

Exit type/speed live on the parent_stage row (the stage<->asset link),
not in the asset's description JSON. NULL means the default exit
("vanish" / 1000 ms, resolved client-side). These tests pin:

  - saveMedia's process_urls writes per-assignment settings and no
    longer touches exitAnimation/exitSpeed keys in the description blob,
  - every delete-recreate assignment path preserves settings for
    stage<->asset pairs that survive the rebuild (via the
    snapshot_exit_settings/make_parent_stage helpers),
  - pairs removed and later re-added start back at NULL.

Pure attribute logic with stub session/asset objects — no DB.
"""

from __future__ import annotations

import json

from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.services.assignment import (
    make_parent_stage,
    snapshot_exit_settings,
)


class _Stages:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def delete(self) -> None:
        self.rows = []

    def append(self, item) -> None:
        self.rows.append(item)


class _Asset:
    def __init__(self, description: str | None = None, rows=None) -> None:
        self.id = 7
        self.description = description
        self.size = 0
        self.stages = _Stages(rows)


class _Query:
    """Mimics session.query(ParentStageModel).filter(...).all()."""

    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_):
        return self

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def query(self, _model):
        return _Query(self._rows)

    def flush(self) -> None:
        pass


def _row(stage_id, asset_id=7, animation=None, speed=None):
    return ParentStageModel(
        stage_id=stage_id,
        child_asset_id=asset_id,
        exit_animation=animation,
        exit_speed=speed,
    )


def _save_input(**overrides):
    from upstage_backend.assets.http.validation import SaveMediaInput

    base = dict(
        name="exit-test",
        mediaType="avatar",
        copyrightLevel=0,
        stageAssignments=[],
        urls=[],
        w=100.0,
        h=100.0,
    )
    base.update(overrides)
    return SaveMediaInput(**base)


def _process(asset, session, **overrides):
    from upstage_backend.assets.services.asset import AssetService

    AssetService().process_urls(
        _save_input(**overrides),
        session,
        None,  # asset_type: only read inside the urls branch, unused here
        asset,
        "",  # file_location: same
    )


def test_save_media_persists_per_assignment_settings() -> None:
    asset = _Asset()
    _process(
        asset,
        _Session(),
        stageAssignments=[
            {"stageId": 1, "exitAnimation": "poof", "exitSpeed": 2500},
            {"stageId": 2},
        ],
    )
    by_stage = {row.stage_id: row for row in asset.stages.rows}
    assert by_stage[1].exit_animation == "poof"
    assert by_stage[1].exit_speed == 2500
    assert by_stage[2].exit_animation is None
    assert by_stage[2].exit_speed is None


def test_save_media_writes_no_exit_keys_to_description() -> None:
    asset = _Asset()
    _process(
        asset,
        _Session(),
        note="keep",
        stageAssignments=[{"stageId": 1, "exitAnimation": "poof", "exitSpeed": 2500}],
    )
    attributes = json.loads(asset.description)
    assert "exitAnimation" not in attributes
    assert "exitSpeed" not in attributes
    assert attributes["note"] == "keep"


def test_save_media_snapshot_preserves_omitted_settings() -> None:
    existing = [_row(1, animation="ghost", speed=4000)]
    asset = _Asset(rows=existing)
    _process(
        asset,
        _Session(existing),
        stageAssignments=[{"stageId": 1}, {"stageId": 2}],
    )
    by_stage = {row.stage_id: row for row in asset.stages.rows}
    assert by_stage[1].exit_animation == "ghost"
    assert by_stage[1].exit_speed == 4000
    assert by_stage[2].exit_animation is None


def test_save_media_explicit_settings_override_snapshot() -> None:
    existing = [_row(1, animation="ghost", speed=4000)]
    asset = _Asset(rows=existing)
    _process(
        asset,
        _Session(existing),
        stageAssignments=[{"stageId": 1, "exitAnimation": "fade", "exitSpeed": 1500}],
    )
    (row,) = asset.stages.rows
    assert (row.exit_animation, row.exit_speed) == ("fade", 1500)


def test_snapshot_and_rebuild_preserves_surviving_pairs() -> None:
    # The assign_media / assign_stages / quickAssignMutation contract:
    # snapshot before delete, rebuild without explicit settings.
    session = _Session([_row(1, animation="sparkle", speed=3000), _row(2)])
    snapshot = snapshot_exit_settings(session, asset_id=7)

    survivor = make_parent_stage(1, 7, snapshot)
    assert (survivor.exit_animation, survivor.exit_speed) == ("sparkle", 3000)

    unset_pair = make_parent_stage(2, 7, snapshot)
    assert (unset_pair.exit_animation, unset_pair.exit_speed) == (None, None)

    # A pair absent from the snapshot (removed earlier, re-added now)
    # starts back at the default.
    readded = make_parent_stage(3, 7, snapshot)
    assert (readded.exit_animation, readded.exit_speed) == (None, None)


def test_partial_explicit_input_keeps_other_field_from_snapshot() -> None:
    # Each field falls back to the snapshot independently: an animation-only
    # update must not wipe a surviving pair's saved speed (and vice versa).
    snapshot = {(1, 7): ("ghost", 4000)}
    row = make_parent_stage(1, 7, snapshot, exit_animation="poof")
    assert (row.exit_animation, row.exit_speed) == ("poof", 4000)
    row = make_parent_stage(1, 7, snapshot, exit_speed=1500)
    assert (row.exit_animation, row.exit_speed) == ("ghost", 1500)


def test_make_parent_stage_coerces_graphql_id_strings() -> None:
    # GraphQL ID inputs arrive as strings; rows and snapshot keys must
    # still line up as ints.
    snapshot = {(1, 7): ("poof", 2000)}
    row = make_parent_stage("1", "7", snapshot)
    assert (row.stage_id, row.child_asset_id) == (1, 7)
    assert (row.exit_animation, row.exit_speed) == ("poof", 2000)
