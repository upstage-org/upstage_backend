"""Per-media exit-animation persistence (saveMedia -> description JSON).

`AssetService.process_urls` is where voice/link/note — and now
exitAnimation/exitSpeed — land in the asset's `description` attribute
blob. These tests exercise that pure attribute logic with stub
session/asset objects, so the contract stays pinned without a DB:

  - a non-empty value persists,
  - the empty sentinel ("" / 0) deletes the stored key ("stage default"),
  - omitted (None) fields leave existing attributes untouched.
"""

from __future__ import annotations

import json


class _Stages:
    def delete(self) -> None:
        pass

    def append(self, _item) -> None:
        pass


class _Asset:
    def __init__(self, description: str | None = None) -> None:
        self.description = description
        self.size = 0
        self.stages = _Stages()


class _Session:
    def flush(self) -> None:
        pass


def _save_input(**overrides):
    from upstage_backend.assets.http.validation import SaveMediaInput

    base = dict(
        name="exit-test",
        mediaType="avatar",
        copyrightLevel=0,
        stageIds=[],
        urls=[],
        w=100.0,
        h=100.0,
    )
    base.update(overrides)
    return SaveMediaInput(**base)


def _process(asset, **overrides):
    from upstage_backend.assets.services.asset import AssetService

    AssetService().process_urls(
        _save_input(**overrides),
        _Session(),
        None,  # asset_type: only read inside the urls branch, unused here
        asset,
        "",  # file_location: same
    )
    return json.loads(asset.description) if asset.description else {}


def test_exit_fields_persist() -> None:
    asset = _Asset()
    attributes = _process(asset, exitAnimation="poof", exitSpeed=2500)
    assert attributes["exitAnimation"] == "poof"
    assert attributes["exitSpeed"] == 2500


def test_exit_sentinel_clears_saved_values() -> None:
    asset = _Asset(json.dumps({"exitAnimation": "poof", "exitSpeed": 2500, "note": "n"}))
    attributes = _process(asset, exitAnimation="", exitSpeed=0)
    assert "exitAnimation" not in attributes
    assert "exitSpeed" not in attributes
    # Sibling attributes survive the rewrite.
    assert attributes["note"] == "n"


def test_omitted_exit_fields_leave_attributes_untouched() -> None:
    original = json.dumps({"exitAnimation": "sparkle", "exitSpeed": 1200})
    asset = _Asset(original)
    # note-only edit: exit fields are None (not provided by the client)
    attributes = _process(asset, note="just a note edit")
    assert attributes["exitAnimation"] == "sparkle"
    assert attributes["exitSpeed"] == 1200
    assert attributes["note"] == "just a note edit"
