# -*- coding: iso8859-15 -*-
"""
End-to-end drift-catching test for the event_archive writer's output shape
against the downstream consumers StageOperationService.get_event_list and
StageService.sweep_stage.
"""
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
srcdir = os.path.abspath(os.path.join(projdir2, "src"))
for _p in (appdir, projdir, projdir2, srcdir):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

import json
import types

import pytest


WRITER_ID = "hentest"
OTHER_WRITER_ID = "other_stage"
NAMESPACE = "production"


def _topic(stage_slug: str, leaf: str) -> str:
    """Mirror the frontend's namespaceTopic(): <ns>/<fileLocation>/<leaf>."""
    return f"{NAMESPACE}/{stage_slug}/{leaf}"


def _persist_via_writer_logic(session, topic: str, raw_payload, ts: float):
    """
    Recreate the writer_loop's per-event persistence body verbatim, minus the
    async plumbing. If writer.py's decode+construct contract drifts, this
    function will need to change in lockstep with it.
    """
    from event_archive.writer import _decode_payload, _PayloadDecodeError
    from event_archive.db_models.event import EventModel

    try:
        payload = _decode_payload(raw_payload)
    except _PayloadDecodeError:
        return None
    event = EventModel(
        topic=topic,
        payload=payload,
        mqtt_timestamp=ts,
        performance_id=None,
    )
    session.add(event)
    session.flush()
    return event


def _seed_stage(session, file_location: str, name: str = "Test Stage"):
    from stages.db_models.stage import StageModel

    stage = StageModel(
        name=name,
        file_location=file_location,
        owner_id=1,
    )
    session.add(stage)
    session.flush()
    return stage


class TestWriterDecodeShape:
    """Pure-function tests that don't need a session."""

    def test_decodes_bytes_json_to_dict(self):
        from event_archive.writer import _decode_payload

        assert _decode_payload(b'{"type":"chat","text":"hi"}') == {
            "type": "chat",
            "text": "hi",
        }

    def test_decodes_str_json_to_dict(self):
        from event_archive.writer import _decode_payload

        assert _decode_payload('{"a":1}') == {"a": 1}

    def test_accepts_json_array(self):
        from event_archive.writer import _decode_payload

        assert _decode_payload(b"[1,2,3]") == [1, 2, 3]

    def test_rejects_invalid_utf8_bytes(self):
        from event_archive.writer import _decode_payload, _PayloadDecodeError

        with pytest.raises(_PayloadDecodeError):
            _decode_payload(b"\xff\xfe\x00bad")

    def test_rejects_non_json_text(self):
        from event_archive.writer import _decode_payload, _PayloadDecodeError

        with pytest.raises(_PayloadDecodeError):
            _decode_payload(b"not json at all")

    def test_rejects_unsupported_payload_type(self):
        from event_archive.writer import _decode_payload, _PayloadDecodeError

        with pytest.raises(_PayloadDecodeError):
            _decode_payload(12345)


class TestWriterPersistAndRead:
    """
    The full drift-catching loop: writer-shaped rows -> get_event_list ->
    sweep_stage -> get_event_list.
    """

    def test_writer_output_is_consumable_by_stage_load_and_sweep(self, rebound_db):
        from global_config import get_session

        setup_session = rebound_db["db_session"]
        stage = _seed_stage(setup_session, file_location=WRITER_ID)
        other_stage = _seed_stage(
            setup_session, file_location=OTHER_WRITER_ID, name="Other"
        )

        chat_payload = {"id": "u1", "nickname": "alice", "text": "hello", "at": 100}
        bg_payload = {"type": "changeBackground", "background": "b1.png", "at": 101}
        board_payload = {
            "type": "placeObjectOnStage",
            "object": {"id": "o1", "x": 0.5, "y": 0.5},
            "at": 102,
        }
        cross_stage_payload = {"text": "not for us"}

        inputs = [
            (_topic(WRITER_ID, "chat"), json.dumps(chat_payload).encode(), 100.0),
            (
                _topic(WRITER_ID, "background"),
                json.dumps(bg_payload).encode(),
                101.0,
            ),
            (
                _topic(WRITER_ID, "board"),
                json.dumps(board_payload),
                102.0,
            ),
            (
                _topic(WRITER_ID, "board"),
                b"\xff\xfe malformed",
                103.0,
            ),
            (
                _topic(OTHER_WRITER_ID, "chat"),
                json.dumps(cross_stage_payload).encode(),
                104.0,
            ),
        ]

        dropped = 0
        persisted_ids = []
        for topic, raw, ts in inputs:
            event = _persist_via_writer_logic(setup_session, topic, raw, ts)
            if event is None:
                dropped += 1
            else:
                persisted_ids.append(event.id)

        setup_session.commit()
        stage_id = stage.id
        stage_file_location = stage.file_location
        other_stage_id = other_stage.id

        assert dropped == 1, "malformed payload should be dropped, matching legacy worker"
        assert len(persisted_ids) == 4

        from event_archive.db_models.event import EventModel

        rows = (
            get_session()
            .query(EventModel)
            .order_by(EventModel.mqtt_timestamp)
            .all()
        )
        assert [r.performance_id for r in rows] == [None, None, None, None]
        for r in rows:
            assert isinstance(r.payload, (dict, list)), (
                "writer must store JSON as a Python value, not a raw string, "
                "so that the GraphQL layer serializes it correctly"
            )

        from stages.services.stage_operation import StageOperationService
        from stages.http.validation import StageStreamInput

        op = StageOperationService()

        class _StageRef:
            def __init__(self, fl):
                self.file_location = fl

        stage_ref = _StageRef(stage_file_location)
        other_ref = _StageRef(OTHER_WRITER_ID)

        live_events = op.get_event_list(
            StageStreamInput(performanceId=None, cursor=None), stage_ref
        )
        assert len(live_events) == 3, (
            "get_event_list should see all valid writer rows for this stage "
            "and skip the malformed one and the cross-stage row"
        )
        assert [e["mqttTimestamp"] for e in live_events] == [100.0, 101.0, 102.0]
        assert live_events[0]["payload"] == chat_payload
        assert live_events[1]["payload"] == bg_payload
        assert live_events[2]["payload"] == board_payload
        assert all(e["performanceId"] is None for e in live_events)

        other_live = op.get_event_list(
            StageStreamInput(performanceId=None, cursor=None), other_ref
        )
        assert len(other_live) == 1, "file_location LIKE must isolate stages"

        from stages.services.stage import StageService

        svc = StageService()
        fake_user = types.SimpleNamespace(id=1)
        sweep_result = svc.sweep_stage(fake_user, stage_id)
        assert sweep_result["success"] is True
        new_performance_id = sweep_result["performanceId"]
        assert isinstance(new_performance_id, int) and new_performance_id > 0

        live_after_sweep = op.get_event_list(
            StageStreamInput(performanceId=None, cursor=None), stage_ref
        )
        assert live_after_sweep == [], (
            "after sweep, no events should remain with performance_id=NULL for "
            "this stage"
        )

        archived = op.get_event_list(
            StageStreamInput(performanceId=new_performance_id, cursor=None),
            stage_ref,
        )
        assert len(archived) == 3
        assert [e["mqttTimestamp"] for e in archived] == [100.0, 101.0, 102.0]
        assert all(e["performanceId"] == new_performance_id for e in archived)
        assert archived[0]["payload"] == chat_payload
        assert archived[1]["payload"] == bg_payload
        assert archived[2]["payload"] == board_payload

        other_live_after_sweep = op.get_event_list(
            StageStreamInput(performanceId=None, cursor=None), other_ref
        )
        assert len(other_live_after_sweep) == 1, (
            "sweep must only touch events belonging to the swept stage's "
            "file_location"
        )

        from graphql import GraphQLError

        with pytest.raises(GraphQLError):
            svc.sweep_stage(fake_user, stage_id)

        _ = other_stage_id
