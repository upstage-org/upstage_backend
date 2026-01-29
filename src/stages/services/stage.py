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

import re
import arrow
from graphql import GraphQLError
import jwt
from requests import Request
from sqlalchemy import and_, nulls_last
from global_config.database import (
    ScopedSession,
)
from global_config.env import ALGORITHM, SECRET_KEY
from global_config.helpers.object import convert_keys_to_camel_case, normalize_datetime_to_naive_utc, get_naive_utc_now

from assets.db_models.asset_usage import AssetUsageModel, NotificationType
from stages.services.stage_operation import StageOperationService
from users.db_models.user import ADMIN, SUPER_ADMIN
from stages.http.validation import (
    DuplicateStageInput,
    SearchStageInput,
    StageInput,
    UpdateStageInput,
    StageStreamInput,
)

from event_archive.db_models.event import EventModel
from performance_config.db_models.performance import PerformanceModel
from performance_config.db_models.scene import SceneModel
from stages.db_models.parent_stage import ParentStageModel
from stages.db_models.stage import StageModel
from stages.db_models.stage_attribute import StageAttributeModel
from users.db_models.user import UserModel
from assets.db_models.asset import AssetModel


class StageService:
    def __init__(self):
        self.stage_operation_service = StageOperationService()

    def get_all_stages(self, user: UserModel, input: SearchStageInput):
        with ScopedSession() as local_db_session:
            query = (
                local_db_session.query(StageModel)
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
                # Normalize dates to timezone-naive UTC for comparison
                start_date = normalize_datetime_to_naive_utc(input.createdBetween[0])
                end_date = normalize_datetime_to_naive_utc(input.createdBetween[1])
                query = query.filter(
                    StageModel.created_on.between(start_date, end_date)
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

            access = input.access if input.access and len(input.access) else ['owner', 'editor', 'player']

            stages = []
            for stage in data:
                permission = self.stage_operation_service.resolve_permission(user.id, stage)
                if permission in access:
                    # Access properties and relationships while object is still attached to session
                    stage_dict = stage.to_dict()
                    cover = stage.cover
                    visibility = stage.visibility
                    status = stage.status
                    # Query assets by stage_id to avoid detached-instance on dynamic relationship (order by id = assign order)
                    parent_stages = (
                        local_db_session.query(ParentStageModel)
                        .filter(ParentStageModel.stage_id == stage.id)
                        .order_by(ParentStageModel.id)
                        .all()
                    )
                    assets_list = [ps.child_asset.to_dict() for ps in parent_stages]
                    stages.append(
                        convert_keys_to_camel_case(
                            {
                                **stage_dict,
                                "cover": cover,
                                "visibility": visibility,
                                "status": status,
                                "permission": permission,
                                "assets": assets_list,
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

            return {
                "edges": paginated_stages,
                "totalCount": total_count,
            }

    def get_stage_list(self, info, input: StageStreamInput):
        request: Request = info.context["request"]
        authorization: str = request.headers.get("Authorization")
        current_user_id = None
        token = authorization.split(" ")[1] if authorization else None

        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_user_id = payload.get("user_id")

        with ScopedSession() as local_db_session:
            query = (
                local_db_session.query(StageModel)
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

            # Process all stages while still in session context to access relationships
            result = []
            for stage in stages:
                stage_dict = stage.to_dict()
                # Query assets by stage_id to avoid detached-instance on dynamic relationship (order by id = assign order)
                parent_stages = (
                    local_db_session.query(ParentStageModel)
                    .filter(ParentStageModel.stage_id == stage.id)
                    .order_by(ParentStageModel.id)
                    .all()
                )
                assets_list = [ps.child_asset.to_dict() for ps in parent_stages]
                cover = stage.cover
                visibility = stage.visibility
                status = stage.status
                
                result.append(
                    convert_keys_to_camel_case(
                        {
                            **stage_dict,
                            "assets": assets_list,
                            "scenes": self.stage_operation_service.get_scene_list(
                                input, stage.id
                            ),
                            "events": self.stage_operation_service.get_event_list(input, stage),
                            "cover": cover,
                            "visibility": visibility,
                            "status": status,
                            "permission": self.stage_operation_service.resolve_permission(
                                current_user_id, stage
                            ),
                            "performances": [
                                convert_keys_to_camel_case(pf)
                                for pf in self.stage_operation_service.resolve_performances(
                                    stage.id
                                )
                            ],
                            "chats": [
                                convert_keys_to_camel_case(chat)
                                for chat in self.stage_operation_service.resolve_chats(
                                    stage.file_location
                                )
                            ],
                        }
                    )
                )
            
            return result

    def get_stage_by_id(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel)
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

            # Convert to dict; query assets by stage_id to avoid detached-instance on dynamic relationship (order by id = assign order)
            stage_dict = stage.to_dict()
            parent_stages = (
                local_db_session.query(ParentStageModel)
                .filter(ParentStageModel.stage_id == stage.id)
                .order_by(ParentStageModel.id)
                .all()
            )
            assets_list = [ps.child_asset.to_dict() for ps in parent_stages]
            
            # Get all stage attributes (to_dict() returns empty array for dynamic relationships)
            stage_attributes = (
                local_db_session.query(StageAttributeModel)
                .filter(StageAttributeModel.stage_id == stage.id)
                .all()
            )
            attributes_list = [
                {
                    "id": attr.id,
                    "name": attr.name,
                    "description": attr.description,
                }
                for attr in stage_attributes
            ]
            
            # Get attribute values using hybrid properties for convenience
            cover = stage.cover
            visibility = stage.visibility
            status = stage.status
            
            # Get playerAccess attribute (no hybrid property, so query directly)
            player_access_attr = (
                local_db_session.query(StageAttributeModel)
                .filter(
                    and_(
                        StageAttributeModel.stage_id == stage.id,
                        StageAttributeModel.name == "playerAccess",
                    )
                )
                .first()
            )
            player_access = player_access_attr.description if player_access_attr else None
            
            performances = [
                convert_keys_to_camel_case(pf)
                for pf in self.stage_operation_service.resolve_performances(
                    stage.id
                )
            ]
            chats = [
                convert_keys_to_camel_case(chat)
                for chat in self.stage_operation_service.resolve_chats(
                    stage.file_location
                )
            ]

            return convert_keys_to_camel_case(
                {
                    **stage_dict,
                    "assets": assets_list,
                    "attributes": attributes_list,  # Include attributes array for frontend
                    "cover": cover,
                    "visibility": visibility,
                    "status": status,
                    "playerAccess": player_access,
                    "permission": permission,
                    "performances": performances,
                    "chats": chats,
                }
            )

    def extract_permission(self, user, stage):
        permission = self.stage_operation_service.resolve_permission(user.id, stage)

        if not stage:
            raise GraphQLError("Stage not found")
        if (
            stage.owner_id != user.id
            and user.role not in [ADMIN, SUPER_ADMIN]
            and permission not in ["editor", "owner"]
        ):
            raise GraphQLError("You are not authorized to update this stage")
        return permission

    def create_stage(self, user: UserModel, input: StageInput):
        with ScopedSession() as local_db_session:
            stage = StageModel(
                name=input.name,
                description=input.description,
                owner_id=input.owner if input.owner else user.id,
                file_location=input.fileLocation,
            )

            local_db_session.add(stage)
            local_db_session.commit()

            self.update_stage_attribute(
                stage.id, "cover", input.cover, local_db_session
            )
            self.update_stage_attribute(
                stage.id, "visibility", str(input.visibility).lower(), local_db_session
            )
            self.update_stage_attribute(
                stage.id, "description", input.description, local_db_session
            )
            self.update_stage_attribute(
                stage.id, "status", input.status, local_db_session
            )
            self.update_stage_attribute(
                stage.id, "playerAccess", input.playerAccess, local_db_session
            )
            # Convert to dict while object is still attached to session
            stage_dict = stage.to_dict()
            return convert_keys_to_camel_case(stage_dict)

    def update_stage(self, user: UserModel, input: UpdateStageInput):
        with ScopedSession() as local_db_session:
            stage = local_db_session.query(StageModel).filter_by(id=input.id).first()
            if not stage or not input.id:
                raise GraphQLError("Stage not found")

            self.extract_permission(user, stage)

            # ALWAYS update all fields with current values from input
            # Frontend should always send all current values, whether changed or not

            # Update core stage fields - use existing value if input is None
            stage.name = input.name if input.name is not None else stage.name
            stage.description = input.description if input.description is not None else stage.description
            stage.file_location = input.fileLocation if input.fileLocation is not None else stage.file_location

            # Update owner_id - preserve existing if not provided or invalid
            if input.owner is not None and str(input.owner).strip() != "":
                try:
                    stage.owner_id = int(input.owner)
                except (ValueError, TypeError):
                    # Invalid owner ID, keep existing owner
                    pass

            # ALWAYS update stage attributes with explicit values
            # This ensures all values are set every time, preventing partial updates

            # Cover - update even if empty/null (use "null" string for None)
            cover_value = str(input.cover) if input.cover is not None else ""
            self.update_stage_attribute(
                stage.id, "cover", cover_value, local_db_session
            )

            # Visibility - ALWAYS update, default to True if not provided
            # Frontend should ALWAYS send this value
            visibility_value = input.visibility if input.visibility is not None else True
            self.update_stage_attribute(
                stage.id, "visibility", str(bool(visibility_value)).lower(), local_db_session
            )

            # Status - ALWAYS update, default to "rehearsal" if not provided or empty
            # Frontend should ALWAYS send "live" or "rehearsal"
            status_value = input.status if (input.status is not None and str(input.status).strip() != "") else "rehearsal"
            self.update_stage_attribute(
                stage.id, "status", str(status_value).lower().strip(), local_db_session
            )

            # PlayerAccess - ALWAYS update, default to empty array if not provided
            # Frontend should ALWAYS send this as JSON string (even "[]")
            player_access_value = input.playerAccess if input.playerAccess is not None else "[]"
            self.update_stage_attribute(
                stage.id, "playerAccess", str(player_access_value), local_db_session
            )

            # Config - ALWAYS update if provided
            # This is optional, so only update if explicitly sent
            if input.config is not None:
                self.update_stage_attribute(
                    stage.id, "config", str(input.config), local_db_session
                )

            local_db_session.commit()
            
            # Expire the stage object to force reload of relationships and hybrid properties
            local_db_session.expire(stage)
            local_db_session.refresh(stage)
            
            # Get all stage attributes (to_dict() returns empty array for dynamic relationships)
            # Query directly from DB to ensure we get the latest values
            stage_attributes = (
                local_db_session.query(StageAttributeModel)
                .filter(StageAttributeModel.stage_id == stage.id)
                .all()
            )
            attributes_list = [
                {
                    "id": attr.id,
                    "name": attr.name,
                    "description": attr.description,
                }
                for attr in stage_attributes
            ]
            
            # Get parent stages for assets
            parent_stages = (
                local_db_session.query(ParentStageModel)
                .filter(ParentStageModel.stage_id == stage.id)
                .order_by(ParentStageModel.id)
                .all()
            )
            assets_list = [ps.child_asset.to_dict() for ps in parent_stages]
            
            # Get attribute values - query directly from DB instead of using hybrid properties
            # to ensure we get the latest values after update
            cover_attr = next((attr for attr in stage_attributes if attr.name == "cover"), None)
            cover = cover_attr.description if cover_attr else None
            
            visibility_attr = next((attr for attr in stage_attributes if attr.name == "visibility"), None)
            visibility = visibility_attr.description == "true" if visibility_attr else False
            
            status_attr = next((attr for attr in stage_attributes if attr.name == "status"), None)
            status = status_attr.description if status_attr else None
            
            player_access_attr = next((attr for attr in stage_attributes if attr.name == "playerAccess"), None)
            player_access = player_access_attr.description if player_access_attr else None
            
            # Get permission
            permission = self.extract_permission(user, stage)
            
            # Convert to dict while object is still attached to session
            stage_dict = stage.to_dict()
            
            # Return the same format as get_stage_by_id
            return convert_keys_to_camel_case(
                {
                    **stage_dict,
                    "assets": assets_list,
                    "attributes": attributes_list,
                    "cover": cover,
                    "visibility": visibility,
                    "status": status,
                    "playerAccess": player_access,
                    "permission": permission,
                }
            )

    def update_stage_attribute(
        self, stage_id: int, name: str, value: str, local_db_session
    ):
        """
        Update or create a stage attribute.
        This method will save the value even if it's an empty string or False.
        Only skips if value is None.
        """
        # Only skip if value is None (not if it's empty string or False)
        if value is None:
            return

        if not stage_id:
            return

        try:
            # Convert value to string to ensure consistency
            value_str = str(value) if value is not None else ""
            
            stage_attribute = (
                local_db_session.query(StageAttributeModel)
                .filter(
                    and_(
                        StageAttributeModel.stage_id == stage_id,
                        StageAttributeModel.name == name,
                    )
                )
                .first()
            )
            
            if stage_attribute:
                # Update existing attribute
                stage_attribute.description = value_str
            else:
                # Create new attribute
                new_attribute = StageAttributeModel(
                    stage_id=stage_id, 
                    name=name, 
                    description=value_str
                )
                local_db_session.add(new_attribute)
            
            # Flush to ensure the change is in the session
            local_db_session.flush()
        except Exception as e:
            # Log the error but don't fail the entire update
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating stage attribute {name} for stage {stage_id}: {str(e)}")
            # Re-raise to see what's wrong
            raise

    def delete_stage(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel).filter(StageModel.id == id).first()
            )
            if not stage:
                raise GraphQLError("Stage not found")

            self.extract_permission(user, stage)

            local_db_session.query(StageAttributeModel).filter(
                StageAttributeModel.stage_id == id
            ).delete()
            local_db_session.query(ParentStageModel).filter(
                ParentStageModel.stage_id == id
            ).delete()

            local_db_session.query(SceneModel).filter(
                SceneModel.stage_id == id
            ).delete()

            performances = local_db_session.query(PerformanceModel).filter(
                PerformanceModel.stage_id == id
            )

            local_db_session.query(EventModel).filter(
                EventModel.performance_id.in_([p.id for p in performances])
            ).delete()

            local_db_session.query(PerformanceModel).filter(
                PerformanceModel.stage_id == id
            ).delete()

            local_db_session.delete(stage)
            return {"success": True, "message": "Stage deleted"}

    def duplicate_stage(self, user: UserModel, input: DuplicateStageInput):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel)
                .filter(StageModel.id == input.id)
                .first()
            )
            if not stage:
                raise GraphQLError("Stage not found")

            file_location = self.get_short_name(input.name, local_db_session)

            new_stage = StageModel(
                name=input.name,
                description=stage.description,
                owner_id=user.id,
                file_location=file_location,
            )

            local_db_session.add(new_stage)
            local_db_session.commit()

            self.copy_data(input, local_db_session, new_stage)

            local_db_session.flush()
            # Convert to dict while object is still attached to session
            new_stage_dict = new_stage.to_dict()
            return convert_keys_to_camel_case(new_stage_dict)

    def copy_data(
        self, input: DuplicateStageInput, local_db_session, new_stage: StageModel
    ):
        stage_attributes = (
            local_db_session.query(StageAttributeModel)
            .filter(StageAttributeModel.stage_id == input.id)
            .all()
        )

        for stage_attribute in stage_attributes:
            self.update_stage_attribute(
                new_stage.id,
                stage_attribute.name,
                stage_attribute.description,
                local_db_session,
            )

        parent_stages = (
            local_db_session.query(ParentStageModel)
            .filter(ParentStageModel.stage_id == input.id)
            .all()
        )
        for parent_stage in parent_stages:
            local_db_session.add(
                ParentStageModel(
                    stage_id=new_stage.id,
                    child_asset_id=parent_stage.child_asset_id,
                )
            )

    def get_short_name(self, name, local_db_session):
        shortname = re.sub(r"\s+", "-", re.sub("[^A-Za-z0-9 ]+", "", name)).lower()

        suffix = ""
        while True:
            existed_stage = (
                local_db_session.query(StageModel)
                .filter(StageModel.file_location == f"{shortname}{suffix}")
                .first()
            )
            if existed_stage:
                suffix = int(suffix or 0) + 1
            else:
                break
        return f"{shortname}{suffix}"

    def sweep_stage(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel).filter(StageModel.id == id).first()
            )
            if not stage:
                raise GraphQLError("Stage not found")

            events = (
                local_db_session.query(EventModel)
                .filter(EventModel.performance_id == None)
                .filter(EventModel.topic.ilike("%/{}/%".format(stage.file_location)))
            )

            if events.count() > 0:
                performance = PerformanceModel(stage_id=stage.id)

                local_db_session.add(performance)
                local_db_session.flush()

                events.update(
                    {EventModel.performance_id: performance.id},
                    synchronize_session="fetch",
                )
            else:
                raise GraphQLError("The stage is already sweeped!")

            performance_id = performance.id
            return convert_keys_to_camel_case(
                {"success": True, "performanceId": performance_id}
            )

    def update_status(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel).filter(StageModel.id == id).first()
            )
            if not stage:
                raise GraphQLError("Stage not found")

            self.extract_permission(user, stage)

            attribute = (
                local_db_session.query(StageAttributeModel)
                .filter(
                    StageAttributeModel.stage_id == id,
                    StageAttributeModel.name == "status",
                )
                .first()
            )

            if attribute is not None:
                attribute.description = (
                    "rehearsal" if attribute.description == "live" else "live"
                )
            else:
                attribute = StageAttributeModel(
                    stage_id=id, name="status", description="live"
                )
            local_db_session.add(attribute)
            local_db_session.commit()
            # Get description while object is still attached to session
            result = attribute.description
            return {"result": result}

    def update_visibility(self, user: UserModel, id: int):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel).filter(StageModel.id == id).first()
            )
            if not stage:
                raise GraphQLError("Stage not found")

            self.extract_permission(user, stage)

            attribute = (
                local_db_session.query(StageAttributeModel)
                .filter(
                    StageAttributeModel.stage_id == id,
                    StageAttributeModel.name == "visibility",
                )
                .first()
            )

            if attribute is not None:
                attribute.description = (
                    "true" if attribute.description != "true" else "false"
                )
            else:
                attribute = StageAttributeModel(
                    stage_id=id, name="visibility", description="true"
                )

            local_db_session.add(attribute)
            local_db_session.commit()
            # Get description while object is still attached to session
            result = attribute.description
            return {"result": result}

    def update_last_access(self, id: int):
        with ScopedSession() as local_db_session:
            stage = (
                local_db_session.query(StageModel).filter(StageModel.id == id).first()
            )
            if not stage:
                raise GraphQLError("Stage not found")

            stage.last_access = get_naive_utc_now()
            local_db_session.commit()
            # Get last_access while object is still attached to session
            result = stage.last_access
            return {"result": result}

    def get_parent_stage(self):
        with ScopedSession() as local_db_session:
            stages = local_db_session.query(ParentStageModel).all()
            # Convert to dicts while objects are still attached to session
            return [
                convert_keys_to_camel_case(stage.to_dict())
                for stage in stages
            ]

    def get_foyer_stage_list(self):
        with ScopedSession() as local_db_session:
            stages = (
                local_db_session.query(StageModel)
                .filter(StageModel.attributes.any(name="visibility", description="true"))
                .order_by(nulls_last(StageModel.last_access.desc()))
                .all()
            )
            # Convert to dicts and access properties while objects are still attached to session
            return [
                {
                    **convert_keys_to_camel_case(stage.to_dict()),
                    "cover": stage.cover,
                }
                for stage in stages
            ]

    def get_notifications(self, user: UserModel):
        with ScopedSession() as local_db_session:
            usages = (
                local_db_session.query(AssetUsageModel)
                .filter(AssetUsageModel.approved == False)
                .filter(AssetUsageModel.asset.has(owner_id=user.id))
                .all()
            )
            # Convert to dicts while objects are still attached to session
            return [
                convert_keys_to_camel_case(
                    {"type": NotificationType.MEDIA_USAGE.value, "mediaUsage": x.to_dict()}
                )
                for x in usages
            ]
