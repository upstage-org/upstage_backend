"""Stage visibility must survive partial updateStage mutations.

The updateStage mutation is also used for partial saves (the Customisation
tab sends only id+config). visibility used to be stringified before the
missing-value guard: str(None) -> "none", a truthy string that overwrote
the stage_attribute row — and "none" != "true" reads as hidden, so every
config-only save silently pulled the stage out of the foyer. These tests
pin the rule: only an explicitly supplied visibility (True/False) is
written; an omitted one leaves the stored attribute untouched.

Pure attribute logic with stub session/stage objects — no DB.
"""

from __future__ import annotations

import pytest

from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
from upstage_backend.stages.http.validation import UpdateStageInput
from upstage_backend.stages.services import stage as stage_module
from upstage_backend.stages.services.stage import StageService


class _Stage:
    def __init__(self):
        self.id = 1
        self.name = "stage"
        self.description = "desc"
        self.file_location = "loc"
        self.owner_id = 1
        # Hybrid-property stand-ins read only for the response payload.
        self.cover = None
        self.visibility = True
        self.status = "live"
        self.playerAccess = None

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class _Attr:
    def __init__(self, name, description):
        self.name = name
        self.description = description


class _AttrQuery:
    """Resolves session.query(StageAttributeModel).filter(and_(...)).first()
    to the stored attribute row matching the name in the filter clause."""

    def __init__(self, attrs):
        self._attrs = attrs
        self._name = None

    def filter(self, clause):
        self._name = clause.clauses[1].right.value
        return self

    def first(self):
        return self._attrs.get(self._name)


class _StageQuery:
    def __init__(self, stage):
        self._stage = stage

    def filter_by(self, **_):
        return self

    def first(self):
        return self._stage


class _Session:
    def __init__(self, stage, attrs):
        self._stage = stage
        self.attrs = attrs
        self.added = []

    def query(self, model):
        if model is StageAttributeModel:
            return _AttrQuery(self.attrs)
        return _StageQuery(self._stage)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        pass


@pytest.fixture
def service(monkeypatch):
    service = StageService()
    monkeypatch.setattr(StageService, "extract_permission", lambda self, user, stage: "owner")
    return service


def _update(monkeypatch, service, attrs, **input_fields):
    session = _Session(_Stage(), attrs)
    monkeypatch.setattr(stage_module, "get_session", lambda: session)
    service.update_stage(None, UpdateStageInput(id=1, **input_fields))
    return session


def test_config_only_update_leaves_visibility_untouched(monkeypatch, service):
    attrs = {"visibility": _Attr("visibility", "true")}
    session = _update(monkeypatch, service, attrs, config="{}")
    assert attrs["visibility"].description == "true"
    assert not any(a.name == "visibility" for a in session.added)


def test_explicit_visibility_false_still_persists(monkeypatch, service):
    attrs = {"visibility": _Attr("visibility", "true")}
    _update(monkeypatch, service, attrs, visibility=False)
    assert attrs["visibility"].description == "false"


def test_explicit_visibility_true_creates_missing_attribute(monkeypatch, service):
    session = _update(monkeypatch, service, {}, visibility=True)
    (added,) = [a for a in session.added if a.name == "visibility"]
    assert added.description == "true"


def test_omitted_status_is_never_written(monkeypatch, service):
    # status has always been guarded by the falsy check; pin it so partial
    # saves can't flip live back to rehearsal either.
    attrs = {"status": _Attr("status", "live")}
    session = _update(monkeypatch, service, attrs, config="{}")
    assert attrs["status"].description == "live"
    assert not any(a.name == "status" for a in session.added)
