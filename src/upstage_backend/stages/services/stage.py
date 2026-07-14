# -*- coding: iso8859-15 -*-

import re
from datetime import datetime
from graphql import GraphQLError
import jwt
from requests import Request
from sqlalchemy import and_, nulls_last, exists
from upstage_backend.global_config import get_session
from upstage_backend.global_config.env import ALGORITHM, SECRET_KEY
from upstage_backend.global_config.helpers.bearer import parse_bearer_token
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case

from upstage_backend.assets.db_models.asset_usage import (
    AssetUsageModel,
    NotificationType,
)
from upstage_backend.stages.services.stage_operation import StageOperationService
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN
from upstage_backend.stages.http.validation import (
    DuplicateStageInput,
    SearchStageInput,
    StageInput,
    UpdateStageInput,
    StageStreamInput,
)

from upstage_backend.event_archive.db_models.event import EventModel
from upstage_backend.performance_config.db_models.performance import PerformanceModel
from upstage_backend.performance_config.db_models.scene import SceneModel
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
from upstage_backend.upstage_stats.db_models.stage_statistic import StageStatisticModel
from upstage_backend.users.db_models.user import UserModel
from upstage_backend.assets.db_models.asset import AssetModel


class StageService:
    def __init__(self):
        self.stage_operation_service = StageOperationService()

    def _stage_stats_map(self, session, file_locations):
        """Return {file_location: {"players", "audiences"}} for the given
        stages, sourced from the counts the upstage_stats worker keeps current
        from retained MQTT statistics. Missing stages simply have no entry."""
        locs = [f for f in file_locations if f]
        if not locs:
            return {}
        rows = (
            session.query(StageStatisticModel).filter(StageStatisticModel.stage_url.in_(locs)).all()
        )
        return {row.stage_url: {"players": row.players, "audiences": row.audiences} for row in rows}

    def get_all_stages(self, user: UserModel, input: SearchStageInput):
        session = get_session()
        query = (
            session.query(StageModel)
            .outerjoin(UserModel)
            .outerjoin(ParentStageModel)
            .outerjoin(AssetModel)
            .group_by(StageModel.id)
        )

        if input.name:
            query = query.filter(StageModel.name.ilike(f"%{input.name}%"))

        if input.owners:
            query = query.filter(UserModel.username.in_(input.owners))

        if input.createdBetween:
            query = query.filter(
                StageModel.created_on.between(input.createdBetween[0], input.createdBetween[1])
            )

        total_count = query.count()

        if input.sort:
            sort = input.sort
            for sort_option in sort:
                field, direction = sort_option.rsplit("_", 1)

                if field == "ACCESS":
                    continue

                if field == "OWNER_ID":
                    sort_field = StageModel.owner_id
                elif field == "NAME":
                    sort_field = StageModel.name
                elif field == "CREATED_ON":
                    sort_field = StageModel.created_on
                elif field == "LAST_ACCESS":
                    sort_field = StageModel.last_access

                if direction == "ASC":
                    query = query.order_by(nulls_last(sort_field.asc()))
                elif direction == "DESC":
                    query = query.order_by(nulls_last(sort_field.desc()))

        else:
            query = query.order_by(StageModel.name.asc())

        data = query.all()

        access = (
            input.access if input.access and len(input.access) else ["owner", "editor", "player"]
        )

        stages = []
        for stage in data:
            permission = self.stage_operation_service.resolve_permission(user.id, stage)
            if permission in access:
                stages.append(
                    convert_keys_to_camel_case(
                        {
                            **stage.to_dict(),
                            "cover": stage.cover,
                            "visibility": stage.visibility,
                            "status": stage.status,
                            "playerAccess": stage.playerAccess,
                            "permission": permission,
                        }
                    )
                )

        total_count = len(stages)

        if input.sort is not None and input.sort[0] in ["ACCESS_DESC", "ACCESS_ASC"]:
            field, direction = input.sort[0].rsplit("_", 1)
            stages.sort(key=lambda s: s["permission"], reverse=(direction == "DESC"))

        limit = input.limit if input.limit else 10
        page = input.page if input.page else 1
        start = (page - 1) * limit
        end = start + limit
        paginated_stages = stages[start:end]

        stats_map = self._stage_stats_map(
            session, [stage.get("fileLocation") for stage in paginated_stages]
        )

        return {
            "edges": [
                {
                    **stage,
                    "assets": [self._asset_with_exit_settings(asset) for asset in stage["assets"]],
                    "players": stats_map.get(stage.get("fileLocation"), {}).get("players", 0),
                    "audiences": stats_map.get(stage.get("fileLocation"), {}).get("audiences", 0),
                }
                for stage in paginated_stages
            ],
            "totalCount": total_count,
        }

    @staticmethod
    def _asset_with_exit_settings(parent_stage):
        """Flatten one stage assignment: the asset dict plus this stage's
        per-assignment exit settings. Keys are camelCase because not every
        caller runs its assets list through convert_keys_to_camel_case."""
        return {
            **parent_stage.child_asset.to_dict(),
            "exitAnimation": parent_stage.exit_animation,
            "exitSpeed": parent_stage.exit_speed,
        }

    def get_stage_list(self, info, input: StageStreamInput):
        session = get_session()
        request: Request = info.context["request"]
        authorization: str = request.headers.get("Authorization")
        current_user_id = None
        token = parse_bearer_token(authorization)

        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_user_id = payload.get("user_id")
            except jwt.ExpiredSignatureError:
                current_user_id = None
            except jwt.InvalidTokenError:
                current_user_id = None

        query = (
            session.query(StageModel)
            .outerjoin(UserModel)
            .outerjoin(StageAttributeModel)
            .outerjoin(ParentStageModel)
            .outerjoin(AssetModel)
            .group_by(StageModel.id)
        )

        if input.fileLocation:
            query = query.filter(StageModel.file_location == input.fileLocation)

        query = query.order_by(StageModel.id)
        stages = query.all()

        return [
            convert_keys_to_camel_case(
                {
                    **stage.to_dict(),
                    "assets": [self._asset_with_exit_settings(asset) for asset in stage.assets],
                    "scenes": self.stage_operation_service.get_scene_list(input, stage.id),
                    "events": self.stage_operation_service.get_event_list(input, stage),
                    "cover": stage.cover,
                    "visibility": stage.visibility,
                    "status": stage.status,
                    "playerAccess": stage.playerAccess,
                    "permission": self.stage_operation_service.resolve_permission(
                        current_user_id, stage
                    ),
                    "performances": [
                        convert_keys_to_camel_case(pf.to_dict())
                        for pf in self.stage_operation_service.resolve_performances(stage.id)
                    ],
                    "chats": [
                        convert_keys_to_camel_case(chat.to_dict())
                        for chat in self.stage_operation_service.resolve_chats(stage.file_location)
                    ],
                }
            )
            for stage in stages
        ]

    def get_stage_by_id(self, user: UserModel, id: int):
        session = get_session()
        stage = (
            session.query(StageModel)
            .outerjoin(UserModel)
            .outerjoin(ParentStageModel)
            .outerjoin(AssetModel)
            .outerjoin(PerformanceModel)
            .outerjoin(SceneModel, SceneModel.stage_id == StageModel.id)
            .outerjoin(EventModel, EventModel.performance_id == PerformanceModel.id)
            .filter(StageModel.id == id)
            .first()
        )

        permission = self.extract_permission(user, stage)

        return convert_keys_to_camel_case(
            {
                **stage.to_dict(),
                "assets": [self._asset_with_exit_settings(asset) for asset in stage.assets],
                "cover": stage.cover,
                "visibility": stage.visibility,
                "status": stage.status,
                "playerAccess": stage.playerAccess,
                "permission": permission,
                "performances": [
                    convert_keys_to_camel_case(pf.to_dict())
                    for pf in self.stage_operation_service.resolve_performances(stage.id)
                ],
                "chats": [
                    convert_keys_to_camel_case(chat.to_dict())
                    for chat in self.stage_operation_service.resolve_chats(stage.file_location)
                ],
            }
        )

    def extract_permission(self, user, stage):
        if not stage:
            raise GraphQLError("Stage not found")

        permission = self.stage_operation_service.resolve_permission(user.id, stage)

        if (
            stage.owner_id != user.id
            and user.role not in [ADMIN, SUPER_ADMIN]
            and permission not in ["editor", "owner"]
        ):
            raise GraphQLError("You are not authorized to update this stage")
        return permission

    def create_stage(self, user: UserModel, input: StageInput):
        session = get_session()
        stage = StageModel(
            name=input.name,
            description=input.description,
            owner_id=input.owner if input.owner else user.id,
            file_location=input.fileLocation,
        )

        session.add(stage)
        session.flush()

        self.update_stage_attribute(stage.id, "cover", input.cover, session)
        self.update_stage_attribute(stage.id, "visibility", str(input.visibility).lower(), session)
        self.update_stage_attribute(stage.id, "description", input.description, session)
        self.update_stage_attribute(stage.id, "status", input.status, session)
        self.update_stage_attribute(stage.id, "playerAccess", input.playerAccess, session)
        # Hybrid properties (cover/visibility/status/playerAccess) live in the
        # stage_attribute table and are NOT enumerated by `to_dict()`. Without
        # explicitly merging them into the return dict the mutation response
        # comes back with those fields = null even when the writes succeeded —
        # callers that read-back from the mutation (e.g. e2e setStageStatus)
        # see a false "did not persist" failure. Mirrors `get_stage_by_id`.
        return convert_keys_to_camel_case(
            {
                **stage.to_dict(),
                "cover": stage.cover,
                "visibility": stage.visibility,
                "status": stage.status,
                "playerAccess": stage.playerAccess,
            }
        )

    def update_stage(self, user: UserModel, input: UpdateStageInput):
        session = get_session()
        stage = session.query(StageModel).filter_by(id=input.id).first()
        if not stage or not input.id:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        stage.name = input.name if hasattr(input, "name") and input.name else stage.name
        stage.description = (
            input.description
            if hasattr(input, "description") and input.description
            else stage.description
        )
        stage.file_location = (
            input.fileLocation
            if hasattr(input, "fileLocation") and input.fileLocation
            else stage.file_location
        )

        stage.owner_id = input.owner if hasattr(input, "owner") and input.owner else stage.owner_id

        self.update_stage_attribute(stage.id, "cover", input.cover, session)
        self.update_stage_attribute(stage.id, "visibility", str(input.visibility).lower(), session)
        self.update_stage_attribute(stage.id, "description", input.description, session)
        self.update_stage_attribute(stage.id, "status", input.status, session)
        self.update_stage_attribute(stage.id, "playerAccess", input.playerAccess, session)
        self.update_stage_attribute(stage.id, "config", input.config, session)
        # Same hybrid-property merge as create_stage; see comment there.
        return convert_keys_to_camel_case(
            {
                **stage.to_dict(),
                "cover": stage.cover,
                "visibility": stage.visibility,
                "status": stage.status,
                "playerAccess": stage.playerAccess,
            }
        )

    def update_stage_attribute(self, stage_id: int, name: str, value: str, session):
        if not value:
            return

        if stage_id:
            stage_attribute = (
                session.query(StageAttributeModel)
                .filter(
                    and_(
                        StageAttributeModel.stage_id == stage_id,
                        StageAttributeModel.name == name,
                    )
                )
                .first()
            )
            if stage_attribute:
                stage_attribute.description = value
                return
            session.add(StageAttributeModel(stage_id=stage_id, name=name, description=value))
            session.flush()

    def delete_stage(self, user: UserModel, id: int):
        session = get_session()
        stage = session.query(StageModel).filter(StageModel.id == id).first()
        if not stage:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        session.query(StageAttributeModel).filter(StageAttributeModel.stage_id == id).delete()
        session.query(ParentStageModel).filter(ParentStageModel.stage_id == id).delete()

        session.query(SceneModel).filter(SceneModel.stage_id == id).delete()

        performances = session.query(PerformanceModel).filter(PerformanceModel.stage_id == id)

        session.query(EventModel).filter(
            EventModel.performance_id.in_([p.id for p in performances])
        ).delete()

        session.query(PerformanceModel).filter(PerformanceModel.stage_id == id).delete()

        session.delete(stage)
        return {"success": True, "message": "Stage deleted"}

    def duplicate_stage(self, user: UserModel, input: DuplicateStageInput):
        session = get_session()
        stage = session.query(StageModel).filter(StageModel.id == input.id).first()
        if not stage:
            raise GraphQLError("Stage not found")

        file_location = self.get_short_name(input.name, session)

        new_stage = StageModel(
            name=input.name,
            description=stage.description,
            owner_id=user.id,
            file_location=file_location,
        )

        session.add(new_stage)
        session.flush()

        self.copy_data(input, session, new_stage)

        session.flush()
        return convert_keys_to_camel_case(new_stage.to_dict())

    def copy_data(self, input: DuplicateStageInput, session, new_stage: StageModel):
        stage_attributes = (
            session.query(StageAttributeModel)
            .filter(StageAttributeModel.stage_id == input.id)
            .all()
        )

        for stage_attribute in stage_attributes:
            self.update_stage_attribute(
                new_stage.id,
                stage_attribute.name,
                stage_attribute.description,
                session,
            )

        parent_stages = (
            session.query(ParentStageModel).filter(ParentStageModel.stage_id == input.id).all()
        )
        for parent_stage in parent_stages:
            session.add(
                ParentStageModel(
                    stage_id=new_stage.id,
                    child_asset_id=parent_stage.child_asset_id,
                    exit_animation=parent_stage.exit_animation,
                    exit_speed=parent_stage.exit_speed,
                )
            )

    def get_short_name(self, name, session):
        shortname = re.sub(r"\s+", "-", re.sub("[^A-Za-z0-9 ]+", "", name)).lower()

        suffix = ""
        while True:
            existed_stage = (
                session.query(StageModel)
                .filter(StageModel.file_location == f"{shortname}{suffix}")
                .first()
            )
            if existed_stage:
                suffix = int(suffix or 0) + 1
            else:
                break
        return f"{shortname}{suffix}"

    def sweep_stage(self, user: UserModel, id: int):
        session = get_session()
        stage = session.query(StageModel).filter(StageModel.id == id).first()
        if not stage:
            raise GraphQLError("Stage not found")

        events = (
            session.query(EventModel)
            .filter(EventModel.performance_id == None)  # noqa: E711  (SQLAlchemy column NULL comparison)
            .filter(EventModel.topic.ilike("%/{}/%".format(stage.file_location)))
        )

        if events.count() > 0:
            performance = PerformanceModel(stage_id=stage.id)

            session.add(performance)
            session.flush()

            events.update(
                {EventModel.performance_id: performance.id},
                synchronize_session="fetch",
            )
        else:
            raise GraphQLError("The stage is already sweeped!")

        return convert_keys_to_camel_case({"success": True, "performanceId": performance.id})

    def update_status(self, user: UserModel, id: int):
        session = get_session()
        stage = session.query(StageModel).filter(StageModel.id == id).first()
        if not stage:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        attribute = (
            session.query(StageAttributeModel)
            .filter(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "status",
            )
            .first()
        )

        if attribute is not None:
            attribute.description = "rehearsal" if attribute.description == "live" else "live"
        else:
            attribute = StageAttributeModel(stage_id=id, name="status", description="live")
            session.add(attribute)
        session.flush()

        attribute = (
            session.query(StageAttributeModel)
            .filter(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "status",
            )
            .first()
        )
        return {"result": attribute.description}

    def update_visibility(self, user: UserModel, id: int):
        session = get_session()
        stage = session.query(StageModel).filter(StageModel.id == id).first()
        if not stage:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        attribute = (
            session.query(StageAttributeModel)
            .filter(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "visibility",
            )
            .first()
        )

        if attribute is not None:
            attribute.description = "true" if attribute.description != "true" else "false"
        else:
            attribute = StageAttributeModel(stage_id=id, name="visibility", description="true")
            session.add(attribute)
        session.flush()

        attribute = (
            session.query(StageAttributeModel)
            .filter(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "visibility",
            )
            .first()
        )

        return {"result": attribute.description}

    def update_last_access(self, id: int):
        session = get_session()
        stage = session.query(StageModel).filter(StageModel.id == id).first()
        if not stage:
            raise GraphQLError("Stage not found")

        stage.last_access = datetime.now()
        session.flush()
        return {"result": stage.last_access}

    def get_parent_stage(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(stage.to_dict())
            for stage in session.query(ParentStageModel).all()
        ]

    def get_foyer_stage_list(self):
        session = get_session()
        # Use explicit EXISTS subquery instead of .any() to avoid transaction issues
        visibility_filter = exists().where(
            and_(
                StageAttributeModel.stage_id == StageModel.id,
                StageAttributeModel.name == "visibility",
                StageAttributeModel.description == "true",
            )
        )

        stages = (
            session.query(StageModel)
            .filter(visibility_filter)
            .order_by(nulls_last(StageModel.last_access.desc()))
            .all()
        )

        result = [
            {
                **convert_keys_to_camel_case(stage.to_dict()),
                "cover": stage.cover,
            }
            for stage in stages
        ]

        stats_map = self._stage_stats_map(session, [stage.get("fileLocation") for stage in result])
        for stage in result:
            stats = stats_map.get(stage.get("fileLocation"), {})
            stage["players"] = stats.get("players", 0)
            stage["audiences"] = stats.get("audiences", 0)

        return result

    def get_notifications(self, user: UserModel):
        """
        Bell entries are derived on the fly from `asset_usage` rows;
        there is no separate notifications table. Three distinct row
        shapes feed the bell, all sharing the GraphQL `Notification`
        envelope and distinguished by `type` so the frontend can pick
        the right copy / action buttons:

          * MEDIA_USAGE (1)            – the asset's *owner* sees a
            pending strict-permission request awaiting approval. The
            owner clears it by approving/declining (existing flow);
            the row leaves the bell once `approved` flips to True
            (and `owner_seen` is set to True at the same time).
          * MEDIA_ACKNOWLEDGEMENT (3)  – the asset's *owner* sees an
            FYI that a player has acknowledged use of one of their
            media items (non-strict copyright levels 0/1/3). No
            action required; clears when the owner dismisses.
          * PERMISSION_APPROVED (2)    – the *requester* sees that
            their strict-permission request was approved. No action
            required; clears when they dismiss.

        Per-recipient dismissal flags (`owner_seen` /
        `requester_seen`) keep the three streams cleanly separated
        even though they share one row: e.g. after the owner
        approves a strict request the row already has
        `owner_seen=True, requester_seen=False`, so it leaves the
        owner's bell and lights up on the requester's bell.
        """
        session = get_session()

        # Owner-side: both pending strict requests (approved=False)
        # and acknowledgement FYIs (approved=True). The same query
        # captures both — they're distinguished by `approved` when we
        # project to the right NotificationType below.
        owner_rows = (
            session.query(AssetUsageModel)
            .filter(AssetUsageModel.owner_seen == False)  # noqa: E712
            .filter(AssetUsageModel.asset.has(owner_id=user.id))
            .all()
        )

        # Requester-side: this user's own approved-and-not-yet-dismissed
        # requests. Strict requests only ever reach `approved=True` via
        # the owner-confirm path, so this naturally maps to "your
        # request was approved" — the new PERMISSION_APPROVED bell.
        requester_rows = (
            session.query(AssetUsageModel)
            .filter(AssetUsageModel.user_id == user.id)
            .filter(AssetUsageModel.approved == True)  # noqa: E712
            .filter(AssetUsageModel.requester_seen == False)  # noqa: E712
            .all()
        )

        notifications = []
        for row in owner_rows:
            notif_type = (
                NotificationType.MEDIA_ACKNOWLEDGEMENT.value
                if row.approved
                else NotificationType.MEDIA_USAGE.value
            )
            notifications.append(
                convert_keys_to_camel_case({"type": notif_type, "mediaUsage": row.to_dict()})
            )

        for row in requester_rows:
            notifications.append(
                convert_keys_to_camel_case(
                    {
                        "type": NotificationType.PERMISSION_APPROVED.value,
                        "mediaUsage": row.to_dict(),
                    }
                )
            )

        return notifications
