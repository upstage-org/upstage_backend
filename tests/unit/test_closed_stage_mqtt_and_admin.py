"""Two follow-ups to the closed-stage rule (#1573).

The broker login must not be handed to the audience of a non-live stage
(with the shared credential they could subscribe to the rehearsal's
topics directly), and an admin must count as an editor of every stage
rather than as audience on the ones not listing them.
"""

from __future__ import annotations

import pytest

from upstage_backend.stages.http import schema as stage_schema
from upstage_backend.stages.services.stage_operation import StageOperationService


@pytest.mark.parametrize(
    ("stage", "has_login"),
    [
        ({"permission": "audience", "status": "rehearsal"}, False),
        ({"permission": "audience", "status": None}, False),
        ({"permission": "audience", "status": "live"}, True),
        ({"permission": "player", "status": "rehearsal"}, True),
        ({"permission": "owner", "status": "upcoming"}, True),
        ({}, False),  # a payload that does not prove the stage is open gets no login either
    ],
)
def test_mqtt_login_withheld_from_the_audience_of_a_closed_stage(stage, has_login):
    login = stage_schema.resolve_stage_mqtt(stage, None)
    assert (login is not None) is has_login
    if login:
        assert set(login) == {"username", "password"}


class _Stage:
    owner_id = 1
    attributes = None


def test_admin_is_editor_of_a_stage_not_listing_them():
    service = StageOperationService()
    assert service.resolve_permission(2, _Stage(), player_access=None, admin=True) == "editor"
    assert service.resolve_permission(1, _Stage(), player_access=None, admin=True) == "owner"
    assert service.resolve_permission(2, _Stage(), player_access=None) == "audience"
    assert service.resolve_permission(None, _Stage(), player_access=None, admin=True) == "audience"
