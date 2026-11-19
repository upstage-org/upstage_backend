"""A stage that is not live is closed to the audience (#1573).

The audience could not get past the Preloader curtain of a rehearsing
stage, but ``stageList`` still handed them the live event log, so their
browser mounted the board behind the curtain and played the performers'
streams and audio. ``live_state_visible`` decides whether the events and
chat go out at all; ``_stage_payload`` applies it.
"""

from __future__ import annotations

import pytest

from upstage_backend.stages.http.validation import StageStreamInput
from upstage_backend.stages.services.stage import StageService


@pytest.mark.parametrize(
    ("permission", "status", "performance_id", "visible"),
    [
        ("audience", "rehearsal", None, False),
        ("audience", "upcoming", None, False),
        ("audience", None, None, False),  # never opened: Stage Management's rehearsal default
        ("audience", "live", None, True),
        ("player", "rehearsal", None, True),
        ("editor", "rehearsal", None, True),
        ("owner", None, None, True),
        ("audience", "rehearsal", 7, True),  # a recording is a separate question
        (None, "rehearsal", None, False),  # resolve_permission falls back to audience
    ],
)
def test_live_state_visible(permission, status, performance_id, visible):
    assert StageService.live_state_visible(permission, status, performance_id) is visible


class _Stage:
    id = 3
    file_location = "rehearsing"

    @staticmethod
    def to_dict():
        return {"id": 3, "name": "Rehearsing"}


class _Operations:
    def __init__(self):
        self.event_calls = 0
        self.chat_calls = 0

    def get_scene_list(self, input, stage_id):
        return []

    def get_event_list(self, input, stage):
        self.event_calls += 1
        return [{"id": 1, "topic": "x/rehearsing/board", "payload": {}}]

    def resolve_performances(self, stage_id):
        return []

    def resolve_chats(self, file_location):
        self.chat_calls += 1
        return []


@pytest.fixture
def service():
    service = StageService()
    service.stage_operation_service = _Operations()
    return service


def test_audience_gets_no_events_or_chat_from_a_rehearsing_stage(service):
    payload = service._stage_payload(
        StageStreamInput(fileLocation="rehearsing"),
        _Stage(),
        {"status": "rehearsal", "visibility": "true"},
        [],
        "audience",
    )
    assert payload["events"] == []
    assert payload["chats"] == []
    assert payload["status"] == "rehearsal"
    assert payload["permission"] == "audience"
    # Not even queried.
    assert service.stage_operation_service.event_calls == 0
    assert service.stage_operation_service.chat_calls == 0


def test_audience_gets_events_from_a_live_stage_and_players_always(service):
    live = service._stage_payload(
        StageStreamInput(fileLocation="rehearsing"), _Stage(), {"status": "live"}, [], "audience"
    )
    assert len(live["events"]) == 1
    player = service._stage_payload(
        StageStreamInput(fileLocation="rehearsing"), _Stage(), {"status": "rehearsal"}, [], "player"
    )
    assert len(player["events"]) == 1
