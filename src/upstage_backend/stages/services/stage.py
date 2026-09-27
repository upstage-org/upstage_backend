import re
from graphql import GraphQLError
import jwt
from starlette.requests import Request
from sqlalchemy import and_, delete, exists, func, nulls_last, or_, select, update
from sqlalchemy.orm import joinedload, selectinload
from upstage_backend.global_config.helpers.clock import utcnow
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
        rows = session.scalars(
            select(StageStatisticModel).where(StageStatisticModel.stage_url.in_(locs))
        ).all()
        return {row.stage_url: {"players": row.players, "audiences": row.audiences} for row in rows}

    # The four stage_attribute rows the list responses expose (StageModel's
    # cover / visibility / status / playerAccess hybrids read the same rows,
    # one query each, per stage).
    _LIST_ATTRIBUTES = ("cover", "visibility", "status", "playerAccess")

    def _stage_attribute_map(self, session, stage_ids):
        """{stage_id: {name: description}} for the list attributes, one query.
        Lowest row id wins when a name is duplicated (the hybrids' `.first()`
        made no such promise)."""
        if not stage_ids:
            return {}
        rows = session.scalars(
            select(StageAttributeModel)
            .where(
                StageAttributeModel.stage_id.in_(stage_ids),
                StageAttributeModel.name.in_(self._LIST_ATTRIBUTES),
            )
            .order_by(StageAttributeModel.id)
        ).all()
        out = {}
        for row in rows:
            out.setdefault(row.stage_id, {}).setdefault(row.name, row.description)
        return out

    @staticmethod
    def _attribute_fields(attrs):
        """The same values StageModel.cover/visibility/status/playerAccess
        produce, from one stage's pre-fetched attribute map."""
        return {
            "cover": attrs.get("cover"),
            "visibility": attrs.get("visibility") == "true",
            "status": attrs.get("status"),
            "playerAccess": attrs.get("playerAccess"),
        }

    def _stage_assets_map(self, session, stage_ids):
        """{stage_id: [ParentStageModel, ...]} in assignment order, with each
        child asset and the relationships its to_dict() walks (type, owner,
        license) loaded in the same round-trip. Iterating `stage.assets`
        (dynamic) and lazy-loading per asset cost 1 + 4 queries per asset."""
        if not stage_ids:
            return {}
        rows = session.scalars(
            select(ParentStageModel)
            .where(ParentStageModel.stage_id.in_(stage_ids))
            .options(
                joinedload(ParentStageModel.child_asset).joinedload(AssetModel.asset_type),
                joinedload(ParentStageModel.child_asset).joinedload(AssetModel.owner),
                joinedload(ParentStageModel.child_asset).joinedload(AssetModel.asset_license),
            )
            .order_by(ParentStageModel.id)
        ).all()
        out = {}
        for row in rows:
            out.setdefault(row.stage_id, []).append(row)
        return out

    def get_all_stages(self, user: UserModel, input: SearchStageInput):
        session = get_session()
        statement = (
            select(StageModel)
            .outerjoin(UserModel)
            .outerjoin(ParentStageModel)
            .outerjoin(AssetModel)
            .group_by(StageModel.id)
            # to_dict() walks `owner`; load it for the whole page at once.
            .options(selectinload(StageModel.owner))
        )

        if input.name:
            # The studio search box matches either the stage name or its URL
            # slug — names and file locations frequently differ.
            pattern = f"%{input.name}%"
            statement = statement.where(
                or_(StageModel.name.ilike(pattern), StageModel.file_location.ilike(pattern))
            )

        if input.owners:
            statement = statement.where(UserModel.username.in_(input.owners))

        if input.createdBetween:
            statement = statement.where(
                StageModel.created_on.between(input.createdBetween[0], input.createdBetween[1])
            )

        if input.sort:
            sort = input.sort
            for sort_option in sort:
                field, direction = sort_option.rsplit("_", 1)

                if field == "ACCESS":
                    continue

                sort_field = {
                    "OWNER_ID": StageModel.owner_id,
                    "NAME": StageModel.name,
                    "CREATED_ON": StageModel.created_on,
                    "LAST_ACCESS": StageModel.last_access,
                }.get(field)
                if sort_field is None:
                    # Unknown key used to leave `sort_field` unbound (or reuse
                    # the previous iteration's column).
                    continue

                if direction == "ASC":
                    statement = statement.order_by(nulls_last(sort_field.asc()))
                elif direction == "DESC":
                    statement = statement.order_by(nulls_last(sort_field.desc()))

        else:
            statement = statement.order_by(StageModel.name.asc())

        data = session.scalars(statement).all()
        attribute_map = self._stage_attribute_map(session, [stage.id for stage in data])

        access = (
            input.access if input.access and len(input.access) else ["owner", "editor", "player"]
        )

        stages = []
        for stage in data:
            attrs = attribute_map.get(stage.id, {})
            permission = self.stage_operation_service.resolve_permission(
                user.id, stage, player_access=attrs.get("playerAccess")
            )
            if permission in access:
                stages.append(
                    convert_keys_to_camel_case(
                        {
                            **stage.to_dict(),
                            **self._attribute_fields(attrs),
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
        assets_map = self._stage_assets_map(session, [stage["id"] for stage in paginated_stages])

        return {
            "edges": [
                {
                    **stage,
                    "assets": [
                        convert_keys_to_camel_case(self._asset_with_exit_settings(asset))
                        for asset in assets_map.get(stage["id"], [])
                    ],
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
        per-assignment exit settings. Every caller camelizes the result
        (directly or via the surrounding stage dict)."""
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

        statement = (
            select(StageModel)
            .outerjoin(UserModel)
            .outerjoin(StageAttributeModel)
            .outerjoin(ParentStageModel)
            .outerjoin(AssetModel)
            .group_by(StageModel.id)
            .options(selectinload(StageModel.owner))
        )

        if input.fileLocation:
            statement = statement.where(StageModel.file_location == input.fileLocation)

        statement = statement.order_by(StageModel.id)
        stages = session.scalars(statement).all()
        stage_ids = [stage.id for stage in stages]
        attribute_map = self._stage_attribute_map(session, stage_ids)
        assets_map = self._stage_assets_map(session, stage_ids)

        return [
            convert_keys_to_camel_case(
                {
                    **stage.to_dict(),
                    "assets": [
                        self._asset_with_exit_settings(asset)
                        for asset in assets_map.get(stage.id, [])
                    ],
                    "scenes": self.stage_operation_service.get_scene_list(input, stage.id),
                    "events": self.stage_operation_service.get_event_list(input, stage),
                    **self._attribute_fields(attribute_map.get(stage.id, {})),
                    "permission": self.stage_operation_service.resolve_permission(
                        current_user_id,
                        stage,
                        player_access=attribute_map.get(stage.id, {}).get("playerAccess"),
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
        stage = session.scalars(
            select(StageModel)
            .outerjoin(UserModel)
            .outerjoin(ParentStageModel)
            .outerjoin(AssetModel)
            .outerjoin(PerformanceModel)
            .outerjoin(SceneModel, SceneModel.stage_id == StageModel.id)
            .outerjoin(EventModel, EventModel.performance_id == PerformanceModel.id)
            .where(StageModel.id == id)
            .limit(1)
        ).first()

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

    # Mirrors the studio form's own check (StageManagement/General.vue); the
    # slug is also the MQTT / event-archive namespace of the stage.
    _STAGE_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

    def _validate_stage_slug(self, session, file_location, exclude_stage_id=None):
        if not isinstance(file_location, str) or not self._STAGE_SLUG_RE.match(file_location):
            raise GraphQLError("Stage URL may only contain letters, digits, '-' and '_'")
        statement = select(StageModel.id).where(StageModel.file_location == file_location)
        if exclude_stage_id is not None:
            statement = statement.where(StageModel.id != exclude_stage_id)
        if session.execute(statement.limit(1)).first() is not None:
            raise GraphQLError("A stage with this URL already exists")

    def create_stage(self, user: UserModel, input: StageInput):
        session = get_session()
        self._validate_stage_slug(session, input.fileLocation)
        # Only admins may create a stage on someone else's behalf.
        owner_id = input.owner if input.owner and user.role in (ADMIN, SUPER_ADMIN) else user.id
        stage = StageModel(
            name=input.name,
            description=input.description,
            owner_id=owner_id,
            file_location=input.fileLocation,
        )

        session.add(stage)
        session.flush()

        self.update_stage_attribute(stage.id, "cover", input.cover, session)
        # visibility must be stringified only when actually supplied:
        # str(None) is the truthy string "none", which used to overwrite the
        # attribute (and "none" != "true" reads as hidden) on every mutation
        # that omitted the field.
        if input.visibility is not None:
            self.update_stage_attribute(
                stage.id, "visibility", str(input.visibility).lower(), session
            )
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
        stage = session.scalars(select(StageModel).filter_by(id=input.id).limit(1)).first()
        if not stage or not input.id:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        def is_owner_or_admin() -> bool:
            return user is not None and (
                stage.owner_id == user.id or user.role in (ADMIN, SUPER_ADMIN)
            )

        stage.name = input.name if hasattr(input, "name") and input.name else stage.name
        stage.description = (
            input.description
            if hasattr(input, "description") and input.description
            else stage.description
        )
        new_slug = getattr(input, "fileLocation", None)
        if new_slug and new_slug != stage.file_location:
            # Editors may not rename the stage URL (it is the stage's MQTT and
            # archive namespace); and it must stay unique.
            if not is_owner_or_admin():
                raise GraphQLError("Only the stage owner or an admin can change the stage URL")
            self._validate_stage_slug(session, new_slug, exclude_stage_id=stage.id)
            stage.file_location = new_slug

        new_owner = getattr(input, "owner", None)
        if new_owner and int(new_owner) != stage.owner_id:
            if not is_owner_or_admin():
                raise GraphQLError("Only the stage owner or an admin can transfer ownership")
            stage.owner_id = new_owner

        self.update_stage_attribute(stage.id, "cover", input.cover, session)
        # Same guard as create_stage: partial updates (e.g. the Customisation
        # tab saves only id+config) must not clobber visibility with "none".
        if input.visibility is not None:
            self.update_stage_attribute(
                stage.id, "visibility", str(input.visibility).lower(), session
            )
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
            stage_attribute = session.scalars(
                select(StageAttributeModel)
                .where(
                    and_(
                        StageAttributeModel.stage_id == stage_id,
                        StageAttributeModel.name == name,
                    )
                )
                .limit(1)
            ).first()
            if stage_attribute:
                stage_attribute.description = value
                return
            session.add(StageAttributeModel(stage_id=stage_id, name=name, description=value))
            session.flush()

    def delete_stage(self, user: UserModel, id: int):
        session = get_session()
        stage = session.scalars(select(StageModel).where(StageModel.id == id).limit(1)).first()
        if not stage:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        session.execute(delete(StageAttributeModel).where(StageAttributeModel.stage_id == id))
        session.execute(delete(ParentStageModel).where(ParentStageModel.stage_id == id))

        session.execute(delete(SceneModel).where(SceneModel.stage_id == id))

        performance_ids = session.scalars(
            select(PerformanceModel.id).where(PerformanceModel.stage_id == id)
        ).all()

        session.execute(delete(EventModel).where(EventModel.performance_id.in_(performance_ids)))

        session.execute(delete(PerformanceModel).where(PerformanceModel.stage_id == id))

        session.delete(stage)
        return {"success": True, "message": "Stage deleted"}

    def duplicate_stage(self, user: UserModel, input: DuplicateStageInput):
        session = get_session()
        stage = session.scalars(
            select(StageModel).where(StageModel.id == input.id).limit(1)
        ).first()
        if not stage:
            raise GraphQLError("Stage not found")
        # Same rule as every other stage mutation: owner, editor or admin.
        self.extract_permission(user, stage)

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
        stage_attributes = session.scalars(
            select(StageAttributeModel).where(StageAttributeModel.stage_id == input.id)
        ).all()

        for stage_attribute in stage_attributes:
            self.update_stage_attribute(
                new_stage.id,
                stage_attribute.name,
                stage_attribute.description,
                session,
            )

        parent_stages = session.scalars(
            select(ParentStageModel).where(ParentStageModel.stage_id == input.id)
        ).all()
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
            existed_stage = session.scalars(
                select(StageModel)
                .where(StageModel.file_location == f"{shortname}{suffix}")
                .limit(1)
            ).first()
            if existed_stage:
                suffix = int(suffix or 0) + 1
            else:
                break
        return f"{shortname}{suffix}"

    def sweep_stage(self, user: UserModel, id: int):
        session = get_session()
        stage = session.scalars(select(StageModel).where(StageModel.id == id).limit(1)).first()
        if not stage:
            raise GraphQLError("Stage not found")

        # Owner / editor / admin only, like every other stage mutation. The
        # resolver's role check alone let ANY logged-in player account sweep
        # ANY stage, including one it is merely audience on (2026-09).
        self.extract_permission(user, stage)

        unswept = (
            EventModel.performance_id == None,  # noqa: E711  (SQLAlchemy column NULL comparison)
            EventModel.topic.ilike("%/{}/%".format(stage.file_location)),
        )

        if session.scalar(select(func.count()).select_from(EventModel).where(*unswept)) > 0:
            performance = PerformanceModel(stage_id=stage.id)

            session.add(performance)
            session.flush()

            session.execute(
                update(EventModel).where(*unswept).values(performance_id=performance.id),
                execution_options={"synchronize_session": "fetch"},
            )
        else:
            raise GraphQLError("The stage is already sweeped!")

        return convert_keys_to_camel_case({"success": True, "performanceId": performance.id})

    def update_status(self, user: UserModel, id: int):
        session = get_session()
        stage = session.scalars(select(StageModel).where(StageModel.id == id).limit(1)).first()
        if not stage:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        attribute = session.scalars(
            select(StageAttributeModel)
            .where(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "status",
            )
            .limit(1)
        ).first()

        if attribute is not None:
            attribute.description = "rehearsal" if attribute.description == "live" else "live"
        else:
            attribute = StageAttributeModel(stage_id=id, name="status", description="live")
            session.add(attribute)
        session.flush()

        attribute = session.scalars(
            select(StageAttributeModel)
            .where(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "status",
            )
            .limit(1)
        ).first()
        return {"result": attribute.description}

    def update_visibility(self, user: UserModel, id: int):
        session = get_session()
        stage = session.scalars(select(StageModel).where(StageModel.id == id).limit(1)).first()
        if not stage:
            raise GraphQLError("Stage not found")

        self.extract_permission(user, stage)

        attribute = session.scalars(
            select(StageAttributeModel)
            .where(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "visibility",
            )
            .limit(1)
        ).first()

        if attribute is not None:
            attribute.description = "true" if attribute.description != "true" else "false"
        else:
            attribute = StageAttributeModel(stage_id=id, name="visibility", description="true")
            session.add(attribute)
        session.flush()

        attribute = session.scalars(
            select(StageAttributeModel)
            .where(
                StageAttributeModel.stage_id == id,
                StageAttributeModel.name == "visibility",
            )
            .limit(1)
        ).first()

        return {"result": attribute.description}

    def update_last_access(self, id: int):
        try:
            id = int(id)
        except (TypeError, ValueError):
            raise GraphQLError("Stage not found") from None
        # Single atomic UPDATE, committed here rather than at request
        # teardown. Ariadne runs sync resolvers on the event loop with a
        # blocking psycopg2 driver, so a row lock must never be held across
        # an ``await``: on 2026-09-19 two audience members loading the same
        # stage 20 ms apart deadlocked prod (A flushed and yielded before the
        # middleware commit; B blocked the loop waiting for A's row lock).
        session = get_session()
        row = session.execute(
            update(StageModel)
            .where(StageModel.id == id)
            .values(last_access=utcnow())
            .returning(StageModel.last_access)
        ).first()
        if row is None:
            session.rollback()
            raise GraphQLError("Stage not found")
        session.commit()
        return {"result": row[0]}

    def get_parent_stage(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(stage.to_dict())
            for stage in session.scalars(select(ParentStageModel)).all()
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

        stages = session.scalars(
            select(StageModel)
            .where(visibility_filter)
            .order_by(nulls_last(StageModel.last_access.desc()))
        ).all()

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
        owner_rows = session.scalars(
            select(AssetUsageModel)
            .where(AssetUsageModel.owner_seen == False)  # noqa: E712
            .where(AssetUsageModel.asset.has(owner_id=user.id))
        ).all()

        # Requester-side: this user's own approved-and-not-yet-dismissed
        # requests. Strict requests only ever reach `approved=True` via
        # the owner-confirm path, so this naturally maps to "your
        # request was approved" — the new PERMISSION_APPROVED bell.
        requester_rows = session.scalars(
            select(AssetUsageModel)
            .where(AssetUsageModel.user_id == user.id)
            .where(AssetUsageModel.approved == True)  # noqa: E712
            .where(AssetUsageModel.requester_seen == False)  # noqa: E712
        ).all()

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
