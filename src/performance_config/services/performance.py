# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

import json
import arrow
from graphql import GraphQLError
from global_config.database import ScopedSession
from global_config.helpers.object import convert_keys_to_camel_case, normalize_datetime_to_naive_utc, get_naive_utc_now
from event_archive.db_models.event import EventModel
from performance_config.db_models.performance import PerformanceModel
from performance_config.db_models.performance_mqtt_config import (
    PerformanceMQTTConfigModel,
)
from performance_config.db_models.performance_config import PerformanceConfigModel
from stages.db_models.stage import StageModel
from stages.http.validation import (
    CreatePerformanceWithEventsInput,
    DuplicatePerformanceInput,
    EventInput,
    PerformanceInput,
    RecordInput,
    SavePerformanceInput,
)
from users.db_models.user import ADMIN, SUPER_ADMIN, UserModel
from sqlalchemy import func
from sqlalchemy.orm.session import make_transient


def _update_performance_duration(session, performance_id):
    """Set performance.duration (ms) from min/max event mqtt_timestamp."""
    row = (
        session.query(
            func.min(EventModel.mqtt_timestamp).label("min_ts"),
            func.max(EventModel.mqtt_timestamp).label("max_ts"),
        )
        .filter(EventModel.performance_id == performance_id)
        .first()
    )
    if row and row.min_ts is not None and row.max_ts is not None:
        delta = row.max_ts - row.min_ts
        # Timestamps may be Unix seconds (large, e.g. 1e9) or relative ms (e.g. 0–1e6)
        duration_ms = int(delta * 1000) if delta < 1e9 else int(delta)
        session.query(PerformanceModel).filter_by(id=performance_id).update(
            {PerformanceModel.duration: duration_ms}
        )


class PerformanceService:
    def __init__(self):
        pass

    def get_performance_communication(self):
        with ScopedSession() as local_db_session:
            return [
                convert_keys_to_camel_case(performance.to_dict())
                for performance in local_db_session.query(PerformanceMQTTConfigModel).all()
            ]

    def get_performance_config(self):
        with ScopedSession() as local_db_session:
            return [
                convert_keys_to_camel_case(performance.to_dict())
                for performance in local_db_session.query(PerformanceConfigModel).all()
            ]

    def create_performance(self, user: UserModel, input: RecordInput):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel).filter_by(id=input.stageId).first()
            )
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

            local_db_session.add(performance)
            local_db_session.commit()
            local_db_session.flush()
            performance = (
                local_db_session.query(PerformanceModel).filter_by(id=performance.id).first()
            )
            # Convert to dict while object is still attached to session
            performance_dict = performance.to_dict()
            return convert_keys_to_camel_case(performance_dict)

    def update_performance(self, user: UserModel, input: PerformanceInput):
        with ScopedSession() as local_db_session:
            performance = (
                local_db_session.query(PerformanceModel).filter_by(id=input.id).first()
            )

            if not performance:
                raise GraphQLError("Performance not found")

            if (
                user.role not in [SUPER_ADMIN, ADMIN]
                and user.id != performance.stage.owner_id
            ):
                raise GraphQLError("You are not allowed to update this performance")

            performance.name = input.name
            performance.description = input.description
            local_db_session.flush()

            return {"success": True}

    def duplicate_performance(self, user: UserModel, input: DuplicatePerformanceInput):
        with ScopedSession() as local_db_session:
            source = (
                local_db_session.query(PerformanceModel)
                .filter_by(id=input.sourceId)
                .first()
            )
            if not source:
                raise GraphQLError("Performance not found")
            if (
                user.role not in [SUPER_ADMIN, ADMIN]
                and user.id != source.stage.owner_id
            ):
                raise GraphQLError("You are not allowed to duplicate this performance")

            new_performance = PerformanceModel(
                name=input.name,
                description=input.description,
                recording=False,
                stage_id=source.stage_id,
            )
            local_db_session.add(new_performance)
            local_db_session.flush()

            events = (
                local_db_session.query(EventModel)
                .filter(EventModel.performance_id == input.sourceId)
                .all()
            )
            for event in events:
                local_db_session.expunge(event)
                make_transient(event)
                event.id = None
                event.performance_id = new_performance.id
                local_db_session.add(event)

            local_db_session.flush()
            new_performance = (
                local_db_session.query(PerformanceModel)
                .filter_by(id=new_performance.id)
                .first()
            )
            return convert_keys_to_camel_case(new_performance.to_dict())

    def save_performance(self, user: UserModel, input: SavePerformanceInput):
        """Save a performance with the given events. Replaces existing performance if performanceId set, else creates new (requires stageId)."""
        with ScopedSession() as local_db_session:
            if input.performanceId is not None:
                performance = (
                    local_db_session.query(PerformanceModel)
                    .filter_by(id=input.performanceId)
                    .first()
                )
                if not performance:
                    raise GraphQLError("Performance not found")
                if (
                    user.role not in [SUPER_ADMIN, ADMIN]
                    and user.id != performance.stage.owner_id
                ):
                    raise GraphQLError("You are not allowed to save over this performance")
                performance.name = input.name
                performance.description = input.description
                local_db_session.query(EventModel).filter(
                    EventModel.performance_id == input.performanceId
                ).delete(synchronize_session=False)
                performance_id = performance.id
            else:
                if input.stageId is None:
                    raise GraphQLError("stageId is required when creating a new performance")
                stage = (
                    local_db_session.query(StageModel).filter_by(id=input.stageId).first()
                )
                if not stage:
                    raise GraphQLError("Stage not found")
                if (
                    user.role not in [SUPER_ADMIN, ADMIN]
                    and user.id != stage.owner_id
                ):
                    raise GraphQLError("You are not allowed to create a performance on this stage")
                performance = PerformanceModel(
                    name=input.name,
                    description=input.description,
                    recording=False,
                    stage_id=input.stageId,
                )
                local_db_session.add(performance)
                local_db_session.flush()
                performance_id = performance.id

            for ev in input.events:
                if ev.payload is None:
                    payload = {}
                elif isinstance(ev.payload, dict):
                    payload = ev.payload
                elif isinstance(ev.payload, str):
                    try:
                        payload = json.loads(ev.payload)
                    except (TypeError, ValueError):
                        payload = {}
                else:
                    payload = {}
                event = EventModel(
                    topic=ev.topic,
                    mqtt_timestamp=ev.mqttTimestamp,
                    performance_id=performance_id,
                    payload=payload,
                )
                local_db_session.add(event)

            local_db_session.flush()
            _update_performance_duration(local_db_session, performance_id)
            performance = (
                local_db_session.query(PerformanceModel).filter_by(id=performance_id).first()
            )
            return convert_keys_to_camel_case(performance.to_dict())

    def create_performance_with_events(
        self, user: UserModel, input: CreatePerformanceWithEventsInput
    ):
        """Create a new performance and save the given events (e.g. compressed replay)."""
        stage_id = int(input.stageId) if input.stageId is not None else None
        if stage_id is None:
            raise GraphQLError("stageId is required")
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel)
                .filter_by(id=stage_id)
                .first()
            )
            if not stage:
                raise GraphQLError("Stage not found")
            if (
                user.role not in [SUPER_ADMIN, ADMIN]
                and user.id != stage.owner_id
            ):
                raise GraphQLError(
                    "You are not allowed to create a performance on this stage"
                )
            performance = PerformanceModel(
                name=input.name,
                description=input.description,
                recording=False,
                stage_id=stage_id,
            )
            local_db_session.add(performance)
            local_db_session.flush()
            performance_id = performance.id

            for ev in input.events:
                if ev.payload is None:
                    payload = {}
                elif isinstance(ev.payload, dict):
                    payload = ev.payload
                elif isinstance(ev.payload, str):
                    try:
                        payload = json.loads(ev.payload)
                    except (TypeError, ValueError):
                        payload = {}
                else:
                    payload = {}
                event = EventModel(
                    topic=ev.topic,
                    mqtt_timestamp=ev.mqttTimestamp,
                    performance_id=performance_id,
                    payload=payload,
                )
                local_db_session.add(event)

            local_db_session.flush()
            _update_performance_duration(local_db_session, performance_id)
            performance = (
                local_db_session.query(PerformanceModel)
                .filter_by(id=performance_id)
                .first()
            )
            return convert_keys_to_camel_case(performance.to_dict())

    def delete_performance(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            performance = (
                local_db_session.query(PerformanceModel).filter_by(id=id).first()
            )
            if not performance:
                raise GraphQLError("Performance not found")

            if (
                user.role not in [SUPER_ADMIN, ADMIN]
                and user.id != performance.stage.owner_id
            ):
                raise GraphQLError("You are not allowed to delete this performance")

            local_db_session.query(EventModel).filter(
                EventModel.performance_id == id
            ).delete(synchronize_session=False)
            local_db_session.delete(performance)
            return {"success": True}

    def save_recording(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            performance = (
                local_db_session.query(PerformanceModel).filter_by(id=id).first()
            )
            if not performance:
                raise GraphQLError("Performance not found")

            if (
                user.role not in [SUPER_ADMIN, ADMIN]
                and user.id != performance.stage.owner_id
            ):
                raise GraphQLError("Only stage owner or Admin can save a recording!")
            saved_on = get_naive_utc_now()
            
            # Normalize datetimes to timezone-naive UTC for SQLAlchemy query comparison
            # SQLAlchemy can handle timezone-aware datetimes, but we ensure consistency
            performance_created_on_naive = normalize_datetime_to_naive_utc(performance.created_on)
            saved_on_naive = normalize_datetime_to_naive_utc(saved_on)

            events_query = (
                local_db_session.query(EventModel)
                .filter(
                    EventModel.topic.ilike(
                        "%/{}/%".format(performance.stage.file_location)
                    )
                )
                .filter(EventModel.created > performance_created_on_naive)
                .filter(EventModel.created < saved_on_naive)
            )

            if events_query.count() > 0:
                for event in events_query.all():
                    local_db_session.expunge(event)
                    make_transient(event)
                    event.id = None
                    event.performance_id = performance.id
                    local_db_session.add(event)
            else:
                raise GraphQLError("Nothing to record!")

            performance.saved_on = saved_on
            performance.recording = False
            local_db_session.flush()

            return (
                local_db_session.query(PerformanceModel)
                .filter_by(id=performance.id)
                .first()
                .to_dict()
            )
