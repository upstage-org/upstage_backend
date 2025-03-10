import json
from event_archive.db_models.event import EventModel
from performance_config.db_models.performance import PerformanceModel
from performance_config.db_models.scene import SceneModel
from global_config.helpers import convert_keys_to_camel_case
from stages.http.validation import StageStreamInput
from stages.db_models.stage_attribute import StageAttributeModel
from stages.db_models.stage import StageModel
from global_config import ScopedSession, DBSession


class StageOperationService:
    def __init__(self):
        pass

    def assign_user_to_default_stage(self, user_ids: int):
        with ScopedSession() as session:
            stage = (
                session.query(StageModel)
                .filter(StageModel.name == "Demo Stage")
                .first()
            )

            playerAccess = stage.attributes.filter(
                StageAttributeModel.name == "playerAccess"
            ).first()

            desc = json.loads(playerAccess.description)

            for uid in user_ids:
                if uid not in desc[0]:
                    desc[0].append(uid)

                # Save the updated list back as a JSON string
            playerAccess.description = json.dumps(desc)
            session.commit()

    def resolve_performances(self, stage_id: int):
        return (
            DBSession.query(PerformanceModel)
            .filter(PerformanceModel.stage_id == stage_id)
            .all()
        )

    def resolve_chats(self, file_location: str):
        return (
            DBSession.query(EventModel)
            .filter(EventModel.topic.like("%/{}/chat".format(file_location)))
            .order_by(EventModel.mqtt_timestamp.asc())
            .all()
        )

    def resolve_permission(self, user_id: int, stage: StageModel):
        if not user_id:
            return "audience"
        if stage.owner_id == user_id:
            return "owner"

        user_id = str(user_id)

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
        cursor = input.cursor if input.cursor else 0
        events = (
            DBSession.query(EventModel)
            .filter(EventModel.performance_id == input.performanceId)
            .filter(EventModel.topic.like("%/{}/%".format(stage.file_location)))
            .filter(EventModel.id > cursor)
            .order_by(EventModel.mqtt_timestamp.asc())
            .all()
        )
        return [convert_keys_to_camel_case(event.to_dict()) for event in events]

    def get_scene_list(self, input: StageStreamInput, stage_id: int):
        query = (
            DBSession.query(SceneModel)
            .filter(SceneModel.stage_id == stage_id)
            .order_by(SceneModel.scene_order.asc())
        )
        if not input.performanceId:  # Only fetch disabled scene in performance replay
            query = query.filter(SceneModel.active == True)
        scenes = query.all()
        return [convert_keys_to_camel_case(scene.to_dict()) for scene in scenes]
