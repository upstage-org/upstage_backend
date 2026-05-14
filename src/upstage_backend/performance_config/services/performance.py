# -*- coding: iso8859-15 -*-

import json
from datetime import datetime
from graphql import GraphQLError
from upstage_backend.global_config import get_session
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.event_archive.db_models.event import EventModel
from upstage_backend.performance_config.db_models.performance import PerformanceModel
from upstage_backend.performance_config.db_models.performance_mqtt_config import (
    PerformanceMQTTConfigModel,
)
from upstage_backend.performance_config.db_models.performance_config import (
    PerformanceConfigModel,
)
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.performance_config.timeline_trim import (
    compress_sorted_times_ms,
    is_chat_topic,
    ms_to_mqtt_storage,
    mqtt_timestamp_to_ms,
)
from upstage_backend.stages.http.validation import (
    DuplicatePerformanceTrimInput,
    PerformanceInput,
    RecordInput,
)
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN, UserModel
from sqlalchemy.orm.session import make_transient


class PerformanceService:
    def __init__(self):
        pass

    def get_performance_communication(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(performance.to_dict())
            for performance in session.query(PerformanceMQTTConfigModel).all()
        ]

    def get_performance_config(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(performance.to_dict())
            for performance in session.query(PerformanceConfigModel).all()
        ]

    def create_performance(self, user: UserModel, input: RecordInput):
        session = get_session()
        stage = session.query(StageModel).filter_by(id=input.stageId).first()
        if not stage:
            raise GraphQLError("Stage not found")

        if user.role not in [SUPER_ADMIN, ADMIN] and user.id != stage.owner_id:
            raise GraphQLError("You are not allowed to record for this stage")

        performance = PerformanceModel(
            name=input.name,
            description=input.description,
            recording=True,
            stage_id=input.stageId,
        )

        session.add(performance)
        session.flush()
        performance = (
            session.query(PerformanceModel).filter_by(id=performance.id).first()
        )
        return convert_keys_to_camel_case(performance)

    def update_performance(self, user: UserModel, input: PerformanceInput):
        session = get_session()
        performance = session.query(PerformanceModel).filter_by(id=input.id).first()

        if not performance:
            raise GraphQLError("Performance not found")

        if (
            user.role not in [SUPER_ADMIN, ADMIN]
            and user.id != performance.stage.owner_id
        ):
            raise GraphQLError("You are not allowed to update this performance")

        performance.name = input.name
        performance.description = input.description
        session.flush()

        return {"success": True}

    def duplicate_performance_with_trimmed_pauses(
        self, user: UserModel, input: DuplicatePerformanceTrimInput
    ):
        session = get_session()
        source = (
            session.query(PerformanceModel)
            .filter_by(id=input.sourcePerformanceId)
            .first()
        )
        if not source:
            raise GraphQLError("Performance not found")

        if (
            user.role not in [SUPER_ADMIN, ADMIN]
            and user.id != source.stage.owner_id
        ):
            raise GraphQLError("You are not allowed to duplicate this performance")

        description = (
            source.description
            if input.description is None
            else input.description
        )

        events = (
            session.query(EventModel)
            .filter(EventModel.performance_id == source.id)
            .order_by(EventModel.id.asc())
            .all()
        )

        if not events:
            raise GraphQLError("Nothing to duplicate: this performance has no events")

        min_pause_ms = float(input.minPauseSeconds) * 1000.0

        def _sort_time_ms(ev: EventModel) -> float:
            pl = ev.payload
            if (
                is_chat_topic(ev.topic)
                and isinstance(pl, dict)
                and isinstance(pl.get("at"), (int, float))
            ):
                return float(pl["at"])
            return mqtt_timestamp_to_ms(ev.mqtt_timestamp)

        ordered = sorted(events, key=lambda e: (_sort_time_ms(e), e.id))
        times_ms = [_sort_time_ms(e) for e in ordered]
        new_times_ms = compress_sorted_times_ms(times_ms, min_pause_ms)

        new_performance = PerformanceModel(
            name=input.name,
            description=description,
            recording=source.recording,
            stage_id=source.stage_id,
            saved_on=source.saved_on,
        )
        session.add(new_performance)
        session.flush()

        for ev, new_ms in zip(ordered, new_times_ms, strict=True):
            payload_out = (
                json.loads(json.dumps(ev.payload))
                if ev.payload is not None
                else None
            )
            if (
                is_chat_topic(ev.topic)
                and isinstance(payload_out, dict)
                and isinstance(payload_out.get("at"), (int, float))
            ):
                payload_out["at"] = int(round(float(new_ms)))

            new_ev = EventModel(
                topic=ev.topic,
                mqtt_timestamp=ms_to_mqtt_storage(ev.mqtt_timestamp, new_ms),
                performance_id=new_performance.id,
                payload=payload_out,
            )
            session.add(new_ev)

        session.flush()
        return convert_keys_to_camel_case(new_performance.to_dict())

    def delete_performance(self, user: UserModel, id: int):
        session = get_session()
        performance = session.query(PerformanceModel).filter_by(id=id).first()
        if not performance:
            raise GraphQLError("Performance not found")

        if (
            user.role not in [SUPER_ADMIN, ADMIN]
            and user.id != performance.stage.owner_id
        ):
            raise GraphQLError("You are not allowed to delete this performance")

        session.query(EventModel).filter(EventModel.performance_id == id).delete(
            synchronize_session=False
        )
        session.delete(performance)
        return {"success": True}

    def save_recording(self, user: UserModel, id: int):
        session = get_session()
        performance = session.query(PerformanceModel).filter_by(id=id).first()
        if not performance:
            raise GraphQLError("Performance not found")

        if (
            user.role not in [SUPER_ADMIN, ADMIN]
            and user.id != performance.stage.owner_id
        ):
            raise GraphQLError("Only stage owner or Admin can save a recording!")
        saved_on = datetime.now()

        events = (
            session.query(EventModel)
            .filter(
                EventModel.topic.ilike("%/{}/%".format(performance.stage.file_location))
            )
            .filter(EventModel.created > performance.created_on)
            .filter(EventModel.created < saved_on)
        )

        if events.count() > 0:
            for event in events.all():
                session.expunge(event)
                make_transient(event)
                event.id = None
                event.performance_id = performance.id
                session.add(event)
        else:
            raise GraphQLError("Nothing to record!")

        performance.saved_on = saved_on
        performance.recording = False
        session.flush()

        return (
            session.query(PerformanceModel)
            .filter_by(id=performance.id)
            .first()
            .to_dict()
        )
