import json

from sqlalchemy import select

from upstage_backend.event_archive.db_models.event import EventModel
from upstage_backend.performance_config.db_models.performance import PerformanceModel
from upstage_backend.performance_config.db_models.scene import SceneModel
from upstage_backend.global_config.helpers import convert_keys_to_camel_case
from upstage_backend.stages.http.validation import StageStreamInput
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.global_config import get_session


class StageOperationService:
    def __init__(self):
        pass

    def assign_user_to_default_stage(self, user_ids: list[int]):
        session = get_session()
        stage = session.scalars(
            select(StageModel).where(StageModel.name == "Demo Stage").limit(1)
        ).first()

        if not stage:
            return

        playerAccess = stage.attributes.filter(StageAttributeModel.name == "playerAccess").first()

        if not playerAccess or not playerAccess.description:
            return

        try:
            desc = json.loads(playerAccess.description)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(desc, list) or len(desc) < 1 or not isinstance(desc[0], list):
            return

        for uid in user_ids:
            if uid not in desc[0]:
                desc[0].append(str(uid))

            # Save the updated list back as a JSON string
        playerAccess.description = json.dumps(desc)

    def resolve_performances(self, stage_id: int):
        session = get_session()
        return session.scalars(
            select(PerformanceModel).where(PerformanceModel.stage_id == stage_id)
        ).all()

    def resolve_chats(self, file_location: str):
        session = get_session()
        return session.scalars(
            select(EventModel)
            .where(EventModel.topic.like("%/{}/chat".format(file_location)))
            .order_by(EventModel.mqtt_timestamp.asc())
        ).all()

    # Sentinel: "caller did not pre-fetch the playerAccess attribute".
    _UNSET = object()

    def resolve_permission(self, user_id: int, stage: StageModel | None, player_access=_UNSET):
        """
        `player_access` may carry the stage's playerAccess attribute value
        (the JSON string, or None when the row does not exist) when the
        caller already loaded the attributes in bulk (StageService list
        paths); otherwise it is read here, one query per stage.
        """
        if stage is None:
            return "audience"
        if not user_id:
            return "audience"
        if stage.owner_id == user_id:
            return "owner"

        user_id = str(user_id)

        if player_access is self._UNSET:
            row = stage.attributes.filter(StageAttributeModel.name == "playerAccess").first()
            player_access = row.description if row else None

        if player_access is not None:
            try:
                accesses = json.loads(player_access)
            except (json.JSONDecodeError, TypeError):
                return "audience"
            if isinstance(accesses, list) and len(accesses) == 2:
                if user_id in accesses[0]:
                    return "player"
                elif user_id in accesses[1]:
                    return "editor"
                return "audience"
        return "audience"

    def get_event_list(self, input: StageStreamInput, stage: StageModel):
        session = get_session()
        cursor = input.cursor if input.cursor else 0
        events = session.scalars(
            select(EventModel)
            .where(EventModel.performance_id == input.performanceId)
            .where(EventModel.topic.like("%/{}/%".format(stage.file_location)))
            .where(EventModel.id > cursor)
            .order_by(EventModel.mqtt_timestamp.asc())
        ).all()
        return [convert_keys_to_camel_case(event.to_dict()) for event in events]

    def get_scene_list(self, input: StageStreamInput, stage_id: int):
        session = get_session()
        statement = (
            select(SceneModel)
            .where(SceneModel.stage_id == stage_id)
            .order_by(SceneModel.scene_order.asc())
        )
        if not input.performanceId:  # Only fetch disabled scene in performance replay
            statement = statement.where(SceneModel.active == True)  # noqa: E712  (SQLAlchemy column comparison)
        scenes = session.scalars(statement).all()
        return [convert_keys_to_camel_case(scene.to_dict()) for scene in scenes]
