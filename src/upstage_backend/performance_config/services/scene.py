# -*- coding: iso8859-15 -*-
import os
import sys

from graphql import GraphQLError
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
            for scene in session.query(SceneModel).all()
        ]

    def create_scene(self, user: UserModel, input: SceneInput):
        session = get_session()
        scene = SceneModel(
            owner_id=user.id,
            stage_id=input.stageId,
            payload=input.payload,
            scene_preview=input.preview,
        )

        scene_order = (
            session.query(SceneModel)
            .filter(SceneModel.stage_id == input.stageId)
            .count()
            + 1
        )

        scene.scene_order = scene_order

        if input.name:
            existed_scene = (
                session.query(SceneModel)
                .filter(SceneModel.stage_id == input.stageId)
                .filter(SceneModel.active == True)
                .filter(SceneModel.name == input.name)
                .first()
            )
            if existed_scene:
                raise GraphQLError(
                    'Scene "{}" already existed. Please choose another name!'.format(
                        input.name
                    )
                )
            scene.name = input.name
        else:
            scene.name = f"Scene {scene_order}"

        session.add(scene)
        session.flush()
        scene = session.query(SceneModel).filter_by(id=scene.id).first()
        return convert_keys_to_camel_case(scene)

    def delete_scene(self, user: UserModel, id: int):
        session = get_session()
        scene = session.query(SceneModel).filter_by(id=id).first()
        if not scene:
            raise GraphQLError("Scene not found")

        if user.role not in [SUPER_ADMIN, ADMIN] and scene.owner_id != user.id:
            raise GraphQLError(
                "You are not allowed to delete this scene",
            )

        scene.active = False
        session.flush()
        return {"success": True, "message": "Scene deleted successfully"}
