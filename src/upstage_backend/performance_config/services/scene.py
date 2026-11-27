from graphql import GraphQLError
from sqlalchemy import func, select
from upstage_backend.global_config import get_session
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.performance_config.db_models.scene import SceneModel
from upstage_backend.stages.http.validation import SceneInput
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN, UserModel


class SceneService:
    def __init__(self):
        pass

    def get_scene(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(scene.to_dict())
            for scene in session.scalars(select(SceneModel)).all()
        ]

    def create_scene(self, user: UserModel, input: SceneInput):
        session = get_session()
        # Deferred import: stages.services.stage is a heavy module and the
        # stage schema imports this service.
        from upstage_backend.stages.db_models.stage import StageModel
        from upstage_backend.stages.services.stage import StageService

        stage = session.scalars(
            select(StageModel).where(StageModel.id == input.stageId).limit(1)
        ).first()
        # Owner / editor / admin only (raises "Stage not found" for None).
        StageService().extract_permission(user, stage)

        scene = SceneModel(
            owner_id=user.id,
            stage_id=input.stageId,
            payload=input.payload,
            scene_preview=input.preview,
        )

        scene_order = (
            session.scalar(
                select(func.count())
                .select_from(SceneModel)
                .where(SceneModel.stage_id == input.stageId)
            )
            + 1
        )

        scene.scene_order = scene_order

        if input.name:
            existed_scene = session.scalars(
                select(SceneModel)
                .where(SceneModel.stage_id == input.stageId)
                .where(SceneModel.active == True)  # noqa: E712  (SQLAlchemy column comparison)
                .where(SceneModel.name == input.name)
                .limit(1)
            ).first()
            if existed_scene:
                raise GraphQLError(
                    'Scene "{}" already existed. Please choose another name!'.format(input.name)
                )
            scene.name = input.name
        else:
            scene.name = f"Scene {scene_order}"

        session.add(scene)
        session.flush()
        scene = session.scalars(select(SceneModel).filter_by(id=scene.id).limit(1)).first()
        return convert_keys_to_camel_case(scene)

    def delete_scene(self, user: UserModel, id: int):
        session = get_session()
        scene = session.scalars(select(SceneModel).filter_by(id=id).limit(1)).first()
        if not scene:
            raise GraphQLError("Scene not found")

        if user.role not in [SUPER_ADMIN, ADMIN] and scene.owner_id != user.id:
            raise GraphQLError(
                "You are not allowed to delete this scene",
            )

        scene.active = False
        session.flush()
        return {"success": True, "message": "Scene deleted successfully"}
