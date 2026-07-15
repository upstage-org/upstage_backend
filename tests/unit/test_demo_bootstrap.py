"""New-installation demo-stage bootstrap.

Two contracts pinned here, both DB-free:

  - The zero-stage gate: scripts/run_bootstrap seeds the demo scaffold only
    when the stage table is empty (a fresh install); --force bypasses for
    controlled dev re-seeding.
  - The shipped seed data (dashboard/demo/seed/demo_stage_seed.json) stays
    consistent with the files next to it and with the runtime contracts that
    consume it — most importantly assign_user_to_default_stage, which finds
    the stage by the exact name "Demo Stage" and appends new players to
    playerAccess[0].

Stub session objects in the style of test_stage_assignment_exit_settings.py.
"""

from __future__ import annotations

import json
import os

from upstage_backend.stages.scripts import bootstrap as bootstrap_module
from upstage_backend.stages.scripts import scaffold_base_media
from upstage_backend.stages.scripts.bootstrap import bootstrap, is_new_installation

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_FOLDER = os.path.join(REPO_ROOT, "dashboard", "demo")
SEED_PATH = os.path.join(DEMO_FOLDER, "seed", "demo_stage_seed.json")


# ---------------------------------------------------------------- gate logic


class _CountQuery:
    def __init__(self, count):
        self._count = count

    def count(self):
        return self._count


class _Session:
    def __init__(self, stage_count):
        self._stage_count = stage_count

    def query(self, _model):
        return _CountQuery(self._stage_count)


class _ScopedSession:
    """Stands in for global_config.database.ScopedSession."""

    def __init__(self, stage_count):
        self._stage_count = stage_count

    def __call__(self):
        return self

    def __enter__(self):
        return _Session(self._stage_count)

    def __exit__(self, *exc):
        return False


def _run(monkeypatch, stage_count, force=False):
    ran = []
    monkeypatch.setattr(bootstrap_module, "ScopedSession", _ScopedSession(stage_count))
    monkeypatch.setattr(bootstrap_module.scaffold_base_media, "main", lambda: ran.append(True))
    result = bootstrap(force=force)
    return result, bool(ran)


def test_is_new_installation_is_zero_stage_count():
    assert is_new_installation(_Session(0)) is True
    assert is_new_installation(_Session(85)) is False


def test_bootstrap_seeds_only_a_fresh_database(monkeypatch):
    result, scaffold_ran = _run(monkeypatch, stage_count=0)
    assert result is True and scaffold_ran


def test_bootstrap_skips_when_stages_exist(monkeypatch):
    # Skip must be a clean False return (run_bootstrap exits 0) — an existing
    # install's migrate container must never fail or reseed.
    result, scaffold_ran = _run(monkeypatch, stage_count=85)
    assert result is False and not scaffold_ran


def test_bootstrap_force_reseeds_despite_existing_stages(monkeypatch):
    result, scaffold_ran = _run(monkeypatch, stage_count=85, force=True)
    assert result is True and scaffold_ran


# ------------------------------------------------------------ seed integrity


def _seed():
    with open(SEED_PATH) as f:
        return json.load(f)


def _all_assets(seed):
    return seed["assets"] + seed.get("unassigned_assets", [])


def _walk_keys(node, banned):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in banned:
                found.append(key)
            found += _walk_keys(value, banned)
    elif isinstance(node, list):
        for value in node:
            found += _walk_keys(value, banned)
    return found


def test_every_seed_file_ships_in_the_demo_folder():
    seed = _seed()
    paths = {seed["stage"]["attributes"]["cover"]}
    for asset in _all_assets(seed):
        paths.add(asset["file_location"])
        paths.update(asset.get("extra_files", []))
        # Multi-frame assets: every frame must be a shipped file too.
        for frame in asset["description"].get("frames", []):
            paths.add(frame)
    for path in sorted(paths):
        assert os.path.isfile(os.path.join(DEMO_FOLDER, path)), (
            f"seed references {path} but dashboard/demo does not ship it"
        )


def test_stage_name_matches_the_default_stage_hook():
    # assign_user_to_default_stage looks the stage up by this exact name;
    # renaming it silently breaks auto-adding new players.
    assert _seed()["stage"]["name"] == "Demo Stage"


def test_player_access_satisfies_the_assignment_contract():
    accesses = json.loads(_seed()["stage"]["attributes"]["playerAccess"])
    assert isinstance(accesses, list) and len(accesses) == 2
    assert all(isinstance(level, list) for level in accesses)


def test_visibility_and_status_are_live_defaults():
    attributes = _seed()["stage"]["attributes"]
    assert attributes["visibility"] == "true"
    assert attributes["status"] == "live"


def test_no_session_state_leaks_into_scene_or_events():
    # `holder` would ship an avatar held by a nonexistent session; nicknames
    # are equally meaningless on a fresh install.
    seed = _seed()
    banned = {"holder", "displayName"}
    assert _walk_keys(seed["scene"]["payload"], banned) == []
    assert _walk_keys(seed["board_events"], banned) == []


def test_board_events_place_the_expected_objects():
    events = _seed()["board_events"]
    assert [e["payload"]["type"] for e in events] == ["placeObjectOnStage"] * 2
    assert {e["payload"]["object"]["name"] for e in events} == {
        "penguin",
        "UpStage logo",
    }


def test_video_asset_ships_its_poster():
    (bunny,) = [a for a in _seed()["assets"] if a["type"] == "video"]
    assert any(f.endswith(".poster.jpg") for f in bunny.get("extra_files", []))


def test_scene_background_is_a_shipped_asset():
    seed = _seed()
    src = seed["scene"]["payload"]["background"]["src"]
    rel = src.removeprefix("/resources/")
    shipped = {a["file_location"] for a in _all_assets(seed)}
    assert rel in shipped, f"scene background {src} is not among the seeded assets"


# -------------------------------------------------------------- idempotency


class _FirstQuery:
    """session.query(...).filter(...).first() returning a fixed row."""

    def __init__(self, row):
        self._row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._row


class _StubStage:
    name = "Demo Stage"
    file_location = "demo"


class _StageSession:
    def __init__(self, existing_stage):
        self._existing = existing_stage
        self.added = []

    def query(self, _model):
        return _FirstQuery(self._existing)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        pass


def test_create_demo_stage_skips_when_stage_exists():
    session = _StageSession(_StubStage())
    stage = scaffold_base_media.create_demo_stage(session, owner_id=1, media=[], seed=_seed())
    assert stage is session._existing
    assert session.added == []


# ------------------------------------------------------ player access grant


class _Attr:
    def __init__(self, description):
        self.name = "playerAccess"
        self.description = description


class _AttrCollection:
    """Mimics the stage.attributes dynamic relationship."""

    def __init__(self, attr):
        self._attr = attr

    def filter(self, *_):
        return self

    def first(self):
        return self._attr


class _AccessStage:
    name = "Demo Stage"

    def __init__(self, attr):
        self.attributes = _AttrCollection(attr)


class _FlushSession:
    def flush(self):
        pass


class _User:
    def __init__(self, uid, username):
        self.id = uid
        self.username = username


def test_grant_player_access_adds_all_users_once():
    # All users existing at seed time land in the player list (index 0);
    # re-granting is a no-op so --force re-runs never duplicate ids.
    attr = _Attr(json.dumps([["1"], []]))
    stage = _AccessStage(attr)
    users = [_User(1, "admin"), _User(2, "guest"), _User(3, "Demo1")]

    scaffold_base_media.grant_player_access(_FlushSession(), stage, users)
    assert json.loads(attr.description) == [["1", "2", "3"], []]

    scaffold_base_media.grant_player_access(_FlushSession(), stage, users)
    assert json.loads(attr.description) == [["1", "2", "3"], []]
