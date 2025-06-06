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

import asyncio
from datetime import datetime
import json
import os
from typing import List

from sqlalchemy import and_, or_, nulls_last

from assets.db_models.asset_usage import AssetUsageModel
from authentication.db_models.user_session import UserSessionModel
from global_config import (
    UPLOAD_USER_CONTENT_FOLDER,
    HOSTNAME,
    DBSession,
    ScopedSession,
    convert_keys_to_camel_case,
    decrypt,
    encrypt,
)
from mails.helpers.mail import send
from mails.templates.templates import (
    display_user,
    notify_owner_of_media_request,
    permission_response_for_media,
    request_permission_acknowledgement,
    request_permission_for_media,
    user_approved,
    waiting_request_media_approve,
)
from performance_config.db_models.performance import PerformanceModel
from stages.services.stage_operation import StageOperationService
from stages.db_models.parent_stage import ParentStageModel
from stages.db_models.stage import StageModel
from assets.db_models.asset import AssetModel
from stages.db_models.stage_attribute import StageAttributeModel
from performance_config.db_models.scene import SceneModel

from studio_management.http.validation import (
    BatchUserInput,
    ChangePasswordInput,
    UpdateUserInput,
)
from users.db_models.user import ADMIN, GUEST, PLAYER, SUPER_ADMIN, UserModel
from graphql import GraphQLError

storagePath = UPLOAD_USER_CONTENT_FOLDER


class StudioService:
    def __init__(self):
        self.stage_operation_service = StageOperationService()
        pass

    def admin_players(self, params):
        query = DBSession.query(UserModel)

        if "usernameLike" in params:
            query = query.filter(
                or_(
                    UserModel.username.ilike(f"%{params['usernameLike']}%"),
                    UserModel.display_name.ilike(f"%{params['usernameLike']}%"),
                    UserModel.last_name.ilike(f"%{params['usernameLike']}%"),
                    UserModel.first_name.ilike(f"%{params['usernameLike']}%"),
                    UserModel.bin_name.ilike(f"%{params['usernameLike']}%"),
                )
            )

        if "createdBetween" in params:
            start_date = datetime.strptime(params["createdBetween"][0], "%Y-%m-%d")
            end_date = datetime.strptime(params["createdBetween"][1], "%Y-%m-%d")
            query = query.filter(UserModel.created_on.between(start_date, end_date))

        if "sort" in params:
            for sort_param in params["sort"]:
                field, direction = sort_param.rsplit("_", 1)
                if field == "USERNAME":
                    sort_field = UserModel.username
                elif field == "ROLE":
                    sort_field = UserModel.role
                elif field == "CREATED_ON":
                    sort_field = UserModel.created_on
                elif field == "EMAIL":
                    sort_field = UserModel.email
                elif field == "LAST_LOGIN":
                    sort_field = UserModel.last_login

                if direction == "ASC":
                    query = query.order_by(nulls_last(sort_field.asc()))
                elif direction == "DESC":
                    query = query.order_by(nulls_last(sort_field.desc()))

        total_count = query.count()

        if "limit" in params:
            limit = params["limit"] or 10
            page = 0 if "page" not in params else (params["page"] - 1)
            offset = page * limit
            query = query.limit(limit).offset(offset)

        results = query.all()

        return convert_keys_to_camel_case(
            {"totalCount": total_count, "edges": [user.to_dict() for user in results]}
        )

    def create_users(self, users: List[BatchUserInput]):
        with ScopedSession() as session:
            self.validate_user_information(users, session)

            for user in users:
                user = UserModel(
                    username=user["username"],
                    email=user["email"],
                    active=True,
                    role=PLAYER,
                    password=encrypt(user["password"]),
                )
                session.add(user)

        users = (
            DBSession.query(UserModel)
            .filter(UserModel.email.in_([user["email"] for user in users]))
            .all()
        )

        self.stage_operation_service.assign_user_to_default_stage(
            [user.id for user in users]
        )

        return convert_keys_to_camel_case({"users": [user.to_dict() for user in users]})

    def validate_user_information(self, users: List[BatchUserInput], session):
        for user in users:
            BatchUserInput(**user)

        duplicated = []
        for i in range(len(users) - 1):
            for j in range(i + 1, len(users)):
                if (
                    users[i]["username"] == users[j]["username"]
                    or users[i]["email"] == users[j]["email"]
                ):
                    duplicated.append(users[i]["username"])

        if duplicated:
            raise GraphQLError(f"Duplicated user information {''.join(duplicated)}")

        existing_users = (
            session.query(UserModel)
            .filter(
                or_(
                    UserModel.username.in_([user["username"] for user in users]),
                    UserModel.email.in_([user["email"] for user in users]),
                )
            )
            .all()
        )

        if existing_users:
            raise GraphQLError(
                f"Users with emails {', '.join([user.email for user in existing_users])} already exist"
            )

    async def update_user(self, input: UpdateUserInput):
        try:
            with ScopedSession() as session:
                self._validate_email(input)
                user = self._get_user(session, input.id)
                self._check_existing_email(input)
                await self._update_user_fields(user, input)
                session.add(user)
                session.flush()
                session.commit()
                user = self._get_user(session, input.id)
                return convert_keys_to_camel_case(user.to_dict())
        except Exception as e:
            raise GraphQLError(
                f"There was an error updating this user information: {str(e)}. Please check the logs and try again later!"
            )

    def _validate_email(self, input: UpdateUserInput):
        if not input.email and input.role != GUEST:
            raise GraphQLError("Email is required!")

    def _get_user(self, session, user_id):
        user = session.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise GraphQLError("User not found!")
        return user

    def _check_existing_email(self, input: UpdateUserInput):
        existing_email = (
            DBSession.query(UserModel)
            .filter(and_(UserModel.email == input.email, UserModel.id != input.id))
            .first()
        )
        if existing_email:
            raise GraphQLError("This email address already belongs to another user!")

    async def _update_user_fields(self, user: UserModel, input: UpdateUserInput):
        if input.password:
            user.password = encrypt(input.password)
        if input.email:
            user.email = input.email
        if input.binName:
            user.bin_name = input.binName
        if input.role:
            user.role = input.role
        if input.firstName:
            user.first_name = input.firstName
        if input.lastName:
            user.last_name = input.lastName
        if input.displayName:
            user.display_name = input.displayName
        if input.active != user.active:
            await self._handle_active_status(user, input.active)
            user.active = input.active
        if input.firebasePushnotId:
            user.firebase_pushnot_id = input.firebasePushnotId
        if input.uploadLimit:
            user.upload_limit = input.uploadLimit
        if input.intro:
            user.intro = input.intro

    async def _handle_active_status(self, user: UserModel, value):
        if value and not user.active and not user.deactivated_on:
            asyncio.create_task(
                send(
                    [user.email],
                    f"Registration approved for user {user.username}",
                    user_approved(user),
                )
            )
        if not value and user.active:
            user.deactivated_on = datetime.now()

    def delete_user(self, id: int, current_user: UserModel):
        with ScopedSession() as local_db_session:
            user = local_db_session.query(UserModel).filter(UserModel.id == id).first()
            if not user:
                raise GraphQLError("User not found!")

            local_db_session.query(UserSessionModel).filter(
                UserSessionModel.user_id == id
            ).delete()

            local_db_session.query(SceneModel).filter(SceneModel.owner_id == id).update(
                {SceneModel.owner_id: current_user.id}
            )

            local_db_session.query(StageModel).filter(StageModel.owner_id == id).update(
                {StageModel.owner_id: current_user.id}
            )
            local_db_session.query(AssetModel).filter(AssetModel.owner_id == id).update(
                {AssetModel.owner_id: current_user.id}
            )

            local_db_session.delete(user)
            return convert_keys_to_camel_case(
                {"success": True, "message": "User deleted successfully!"}
            )

    def change_password(self, input: ChangePasswordInput):
        with ScopedSession() as local_db_session:
            user = (
                local_db_session.query(UserModel)
                .filter(UserModel.id == input.id)
                .first()
            )
            if not user:
                raise GraphQLError("User not found!")

            if decrypt(user.password) != input.oldPassword:
                raise GraphQLError("Old password is incorrect!")

            user.password = encrypt(input.newPassword)
            local_db_session.flush()
            return convert_keys_to_camel_case(
                {"success": True, "message": "Password changed successfully!"}
            )

    def calc_sizes(self):
        with ScopedSession() as local_db_session:
            size = 0
            for media in local_db_session.query(AssetModel).all():
                if not media.size:
                    full_path = os.path.join(storagePath, media.file_location)
                    try:
                        size = os.path.getsize(full_path)
                    except:
                        size = 0  # file not exist
                    media.size = size
                    local_db_session.flush()
                size += media.size

        return {"size": size}

    async def request_permission(self, user: UserModel, asset_id: int, note: str):
        with ScopedSession() as local_db_session:
            asset = (
                local_db_session.query(AssetModel)
                .filter(AssetModel.id == asset_id)
                .first()
            )
            if not asset:
                raise GraphQLError("Asset not found!")
            asset_usage = AssetUsageModel(
                user_id=user.id,
                asset_id=asset_id,
                note=note,
                approved=False,
                seen=False,
            )

            if asset.copyright_level == 2:
                asset_usage.approved = False
                studio_url = f"https://{HOSTNAME}/media"
                asyncio.create_task(
                    send(
                        [asset.owner.email],
                        f"{display_user(user)} wants to use your media {asset.name}",
                        request_permission_for_media(
                            user, asset, note if note else "", studio_url
                        ),
                    )
                )
                asyncio.create_task(
                    send(
                        [user.email],
                        "Your permission request is waiting for approval",
                        waiting_request_media_approve(user, asset),
                    )
                )
            else:
                asset_usage.approved = True

                description = json.loads(asset.description)

                asyncio.create_task(
                    send(
                        [user.email],
                        f"Media acknowledgement",
                        request_permission_acknowledgement(
                            user,
                            asset,
                            note if note else "",
                            description.get("note", ""),
                        ),
                    )
                )

                asyncio.create_task(
                    send(
                        [asset.owner.email],
                        f"{display_user(user)} is using your media {asset.name}",
                        notify_owner_of_media_request(user, asset),
                    )
                )
            local_db_session.add(asset_usage)
            local_db_session.flush()
        return {"success": True}

    async def confirm_permission(self, user: UserModel, id: int, approved: bool):
        with ScopedSession() as local_db_session:
            asset_usage = (
                local_db_session.query(AssetUsageModel)
                .filter(AssetUsageModel.id == id)
                .first()
            )
            if not asset_usage:
                raise GraphQLError("Asset not found!")
            if (
                user.role not in [SUPER_ADMIN, ADMIN]
                and user.id != asset_usage.asset.owner_id
            ):
                raise GraphQLError("You are not authorized to perform this action!")

            if approved:
                asset_usage.approved = True
                asset_usage.seen = True
            else:
                local_db_session.delete(asset_usage)

            studio_url = f"https://{HOSTNAME}/media"
            asyncio.create_task(
                send(
                    [asset_usage.user.email],
                    f"Permission approved for media {asset_usage.asset.name}"
                    if approved
                    else f"Permission denied for media {asset_usage.asset.name}",
                    permission_response_for_media(
                        asset_usage.user,
                        asset_usage.asset,
                        asset_usage.note,
                        approved,
                        studio_url,
                    ),
                )
            )
            local_db_session.flush()
            permissions = (
                local_db_session.query(AssetUsageModel)
                .filter(AssetUsageModel.asset_id == asset_usage.asset_id)
                .all()
            )

            return convert_keys_to_camel_case(
                {
                    "permissions": [
                        convert_keys_to_camel_case(permission.to_dict())
                        for permission in permissions
                    ],
                    "success": True,
                },
            )

    def quick_assign_mutation(
        self, user: UserModel, stage_ids: list[int], asset_id: int
    ):
        with ScopedSession() as local_db_session:
            local_db_session.query(ParentStageModel).filter(
                ParentStageModel.child_asset_id == asset_id
            ).delete()
            local_db_session.flush()

            for stage_id in stage_ids:
                asset = (
                    local_db_session.query(AssetModel)
                    .filter(AssetModel.id == asset_id)
                    .first()
                )
                if not asset:
                    raise GraphQLError("Asset not found!")

                stage = (
                    local_db_session.query(StageModel)
                    .filter(StageModel.id == stage_id)
                    .first()
                )
                if not stage:
                    raise GraphQLError("Stage not found!")

                asset.stages.append(
                    ParentStageModel(stage_id=stage_id, child_asset_id=asset_id)
                )
                local_db_session.flush()
        return {"success": True}

    def get_users(self, active: bool):
        return [
            convert_keys_to_camel_case(user.to_dict())
            for user in DBSession.query(UserModel)
            .filter(UserModel.active == active)
            .order_by(UserModel.username.asc())
            .all()
        ]

    def stages(self, user: UserModel):
        return [
            convert_keys_to_camel_case(
                {
                    **stage.to_dict(),
                    "permission": self.stage_operation_service.resolve_permission(
                        user.id, stage
                    ),
                }
            )
            for stage in DBSession.query(StageModel).order_by(StageModel.name.asc()).all()
        ]
