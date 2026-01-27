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
from event_archive.db_models.event import EventModel
from performance_config.db_models.performance import PerformanceModel
from performance_config.db_models.scene import SceneModel
from global_config.helpers import convert_keys_to_camel_case
from stages.http.validation import StageStreamInput
from stages.db_models.stage_attribute import StageAttributeModel
from stages.db_models.stage import StageModel
from global_config.database import ScopedSession


class StageOperationService:
    def __init__(self):
        pass

    def assign_user_to_default_stage(self, user_ids: list[int]):
        with ScopedSession() as session:
            stage = (
                session.query(StageModel)
                .filter(StageModel.name == "Demo Stage")
                .first()
            )

            if (not stage):
                return

            playerAccess = stage.attributes.filter(
                StageAttributeModel.name == "playerAccess"
            ).first()

            desc = json.loads(playerAccess.description)

            for uid in user_ids:
                if uid not in desc[0]:
                    desc[0].append(str(uid))

                # Save the updated list back as a JSON string
            playerAccess.description = json.dumps(desc)
            session.commit()

    def resolve_performances(self, stage_id: int):
        with ScopedSession() as local_db_session:
            performances = (
                local_db_session.query(PerformanceModel)
                .filter(PerformanceModel.stage_id == stage_id)
                .all()
            )
            # Convert to dicts while objects are still attached to session
            return [performance.to_dict() for performance in performances]

    def resolve_chats(self, file_location: str):
        with ScopedSession() as local_db_session:
            chats = (
                local_db_session.query(EventModel)
                .filter(EventModel.topic.like("%/{}/chat".format(file_location)))
                .order_by(EventModel.mqtt_timestamp.asc())
                .all()
            )
            # Convert to dicts while objects are still attached to session
            return [chat.to_dict() for chat in chats]

    def resolve_permission(self, user_id: int, stage: StageModel):
        if not user_id:
            return "audience"
        if stage.owner_id == user_id:
            return "owner"

        user_id = str(user_id)

        # Check if stage is attached to a session, if not, reload it
        from sqlalchemy.orm import object_session
        session = object_session(stage)
        if session is None:
            # Stage is detached, reload in new session
            with ScopedSession() as local_db_session:
                stage = local_db_session.query(StageModel).filter_by(id=stage.id).first()
                player_access = stage.attributes.filter(
                    StageAttributeModel.name == "playerAccess"
                ).first()
        else:
            # Stage is still attached, access attributes now
            player_access = stage.attributes.filter(
                StageAttributeModel.name == "playerAccess"
            ).first()

        if player_access:
            accesses = json.loads(player_access.description)
            if len(accesses) == 2:
                if user_id in accesses[0]:
                    return "player"
                elif user_id in accesses[1]:
                    return "editor"
                return "audience"
        return "audience"

    def get_event_list(self, input: StageStreamInput, stage: StageModel):
        with ScopedSession() as local_db_session:
            cursor = input.cursor if input.cursor else 0
            events = (
                local_db_session.query(EventModel)
                .filter(EventModel.performance_id == input.performanceId)
                .filter(EventModel.topic.like("%/{}/%".format(stage.file_location)))
                .filter(EventModel.id > cursor)
                .order_by(EventModel.mqtt_timestamp.asc())
                .all()
            )
            return [convert_keys_to_camel_case(event.to_dict()) for event in events]

    def get_scene_list(self, input: StageStreamInput, stage_id: int):
        with ScopedSession() as local_db_session:
            query = (
                local_db_session.query(SceneModel)
                .filter(SceneModel.stage_id == stage_id)
                .order_by(SceneModel.scene_order.asc())
            )
            if not input.performanceId:  # Only fetch disabled scene in performance replay
                query = query.filter(SceneModel.active == True)
            scenes = query.all()
            return [convert_keys_to_camel_case(scene.to_dict()) for scene in scenes]
