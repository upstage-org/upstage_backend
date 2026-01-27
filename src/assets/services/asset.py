# -*- coding: iso8859-15 -*-
import asyncio
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from datetime import datetime, timedelta
import hashlib
import json
from operator import or_
import os
from typing import Optional
import time
from graphql import GraphQLError


from global_config.database import ScopedSession
from global_config.env import (
    UPLOAD_USER_CONTENT_FOLDER,
    STREAM_EXPIRY_DAYS,
    STREAM_KEY,
)
from global_config.helpers.object import convert_keys_to_camel_case
from sqlalchemy.orm import joinedload, selectinload, contains_eager
from assets.db_models.asset import AssetModel, AvatarVoice, Voice, Previlege
from assets.db_models.asset_license import AssetLicenseModel
from assets.db_models.asset_type import AssetTypeModel
from assets.db_models.asset_usage import AssetUsageModel
from assets.db_models.media_tag import MediaTagModel
from assets.db_models.tag import TagModel
from assets.http.validation import (
    MediaTableInput,
    SaveMediaInput,
    UpdateMediaStatusInput,
    MediaStatusEnum,
)
from stages.db_models.stage import StageModel
from stages.db_models.parent_stage import ParentStageModel
from users.db_models.user import ADMIN, PLAYER, SUPER_ADMIN, UserModel
from files.file_handling import FileHandling
from mails.helpers.mail import send
from mails.templates.templates import notify_mark_media_active


storagePath = UPLOAD_USER_CONTENT_FOLDER


class AssetService:
    def __init__(self):
        self.file_handing = FileHandling()
        pass

    def get_all_medias(self, user: UserModel, filter: dict = None):
        with ScopedSession() as local_db_session:
            query = (
                local_db_session.query(AssetModel)
                .join(UserModel, AssetModel.owner_id == UserModel.id)
                .options(contains_eager(AssetModel.owner))
                .join(AssetTypeModel)
                .outerjoin(AssetLicenseModel)
                .outerjoin(
                    ParentStageModel, AssetModel.id == ParentStageModel.child_asset_id
                )
                .outerjoin(StageModel, ParentStageModel.stage_id == AssetModel.id)
                .filter(AssetModel.dormant.is_not(True))
                .order_by(AssetModel.created_on.desc())
            )

            if "mediaType" in filter:
                query = query.filter(AssetTypeModel.name == filter["mediaType"])

            if "owner" in filter:
                query = query.filter(UserModel.username == filter["owner"])

            assets = query.all()
            
            # Materialize owner relationships while session is active
            for asset in assets:
                _ = asset.owner  # Access to materialize the relationship
            
            # Process all assets while still in session context to access relationships
            return [self.resolve_fields(asset, user) for asset in assets]

    def search_assets(self, user: UserModel, search_assets: MediaTableInput):
        # Extract user attributes early to avoid accessing detached user object
        user_role = user.role if user else None
        user_id_value = user.id if user else None
        
        with ScopedSession() as local_db_session:
            query = (
                local_db_session.query(AssetModel)
                .join(UserModel, AssetModel.owner_id == UserModel.id)
                .options(contains_eager(AssetModel.owner))
                .join(AssetTypeModel)
                .outerjoin(AssetLicenseModel)
                .outerjoin(
                    ParentStageModel, AssetModel.id == ParentStageModel.child_asset_id
                )
                .outerjoin(StageModel, ParentStageModel.stage_id == AssetModel.id)
                .group_by(AssetModel.id)
            )

            if user_role not in [SUPER_ADMIN, ADMIN]:
                query = query.filter(AssetModel.dormant.is_not(True))
            elif search_assets.dormant is not None:
                query = query.filter(AssetModel.dormant.is_(search_assets.dormant))

            if search_assets.name:
                query = query.filter(AssetModel.name.ilike(f"%{search_assets.name}%"))
            if search_assets.mediaTypes:
                query = query.filter(AssetTypeModel.name.in_(search_assets.mediaTypes))
            if search_assets.owners:
                query = query.filter(UserModel.username.in_(search_assets.owners))

            if search_assets.stages:
                query = query.filter(
                    AssetModel.stages.any(
                        ParentStageModel.stage_id.in_(search_assets.stages)
                    )
                )
            if search_assets.tags:
                query = (
                    query.join(MediaTagModel)
                    .join(TagModel)
                    .filter(TagModel.name.in_(search_assets.tags))
                )
            if search_assets.createdBetween:
                query = query.filter(
                    AssetModel.created_on.between(
                        search_assets.createdBetween[0], search_assets.createdBetween[1]
                    )
                )

            total_count = query.count()

            if search_assets.sort:
                sort_option = search_assets.sort[-1]
                field, direction = sort_option.rsplit("_", 1)
                if field == "ASSET_TYPE_ID":
                    sort_field = AssetModel.asset_type_id
                elif field == "OWNER_ID":
                    sort_field = AssetModel.owner_id
                elif field == "NAME":
                    sort_field = AssetModel.name
                elif field == "CREATED_ON":
                    sort_field = AssetModel.created_on
                elif field == "SIZE":
                    sort_field = AssetModel.size
                elif field == "COPYRIGHT_LEVEL":
                    sort_field = AssetModel.copyright_level

                if direction == "ASC":
                    query = query.order_by(sort_field.asc())
                elif direction == "DESC":
                    query = query.order_by(sort_field.desc())

            if search_assets.page and search_assets.limit:
                query = query.limit(search_assets.limit).offset(
                    (search_assets.page - 1) * search_assets.limit
                )
            assets = query.all()

            # Materialize owner relationships while session is active
            for asset in assets:
                _ = asset.owner  # Access to materialize the relationship

            # Process all assets while still in session context
            edges = []
            for asset in assets:
                asset_dict = asset.to_dict()
                # Access relationships while object is still attached to session
                # Materialize dynamic relationship by converting to list while session is active
                stages_list = [
                    convert_keys_to_camel_case(item.stage.to_dict())
                    for item in asset.stages.all()  # Use .all() to materialize the dynamic relationship
                ]
                permissions_list = [
                    convert_keys_to_camel_case(permission)
                    for permission in self.resolve_permissions(asset.id)
                ]
                # Extract owner data while session is active
                owner_dict = convert_keys_to_camel_case(asset.owner.to_dict()) if asset.owner else None
                # Extract asset attributes for resolve_privilege while still in session
                asset_owner_id = asset.owner_id
                asset_copyright_level = asset.copyright_level
                asset_id = asset.id
                edges.append({
                    **convert_keys_to_camel_case(asset_dict),
                    "privilege": self.resolve_privilege_from_values(user_id_value, asset_owner_id, asset_copyright_level, asset_id),
                    "stages": stages_list,
                    "permissions": permissions_list,
                    "owner": owner_dict,
                })

            return {
                "totalCount": total_count,
                "edges": edges,
            }

    def upload_file(self, user: UserModel, base64: str, filename: str):
        # Extract user attributes early to avoid accessing detached user object
        upload_limit = user.upload_limit if user else None
        
        file_size = self.file_handing.get_file_size(base64)

        if file_size > upload_limit:
            raise GraphQLError(
                f"File size must be under {self.file_handing.convert_KB_to_MB(upload_limit)}MB."
            )

        file_location = self.file_handing.upload_file(
            base64, filename, None, storagePath, "media"
        )
        return {"url": file_location}

    def save_media(self, owner: UserModel, input: SaveMediaInput):
        asset = None
        with ScopedSession() as local_db_session:
            asset_type = self.validate_asset_type(input, local_db_session)

            if input.id:
                asset = (
                    local_db_session.query(AssetModel)
                    .filter(AssetModel.id == input.id)
                    .first()
                )
                if (
                    owner.role not in [SUPER_ADMIN, ADMIN]
                    and asset.owner_id != owner.id
                ):
                    raise GraphQLError("You are not allowed to update this asset")
            else:
                asset = AssetModel(owner_id=owner.id)
                local_db_session.add(asset)

            asset.name = input.name
            asset.asset_type_id = asset_type.id
            asset.copyright_level = input.copyrightLevel
            file_location = self.process_file_location(input, local_db_session, asset)

            self.change_owner(input.owner, local_db_session, asset)

            self.process_urls(input, local_db_session, asset_type, asset, file_location)

            self.update_asset_permissions(input, local_db_session, asset)
            asset = self.update_asset_tags(input, local_db_session, asset)
            local_db_session.commit()
            local_db_session.flush()

            return convert_keys_to_camel_case({"asset": {"id": asset.id}})

    def update_asset_tags(
        self, input: SaveMediaInput, local_db_session, asset: AssetModel
    ):
        if input.tags:
            tags = input.tags
            asset.tags.delete()
            for tag in tags:
                tag_model = (
                    local_db_session.query(TagModel)
                    .filter(TagModel.name == tag)
                    .first()
                )
                if not tag_model:
                    tag_model = TagModel(name=tag)
                    local_db_session.add(tag_model)
                    local_db_session.flush()
                asset.tags.append(MediaTagModel(tag_id=tag_model.id))

            local_db_session.flush()
            asset = (
                local_db_session.query(AssetModel)
                .filter(AssetModel.id == asset.id)
                .first()
            )

        return asset

    def create_asset(
        self,
        owner: UserModel,
        asset_type_id: int,
        name: str,
        file_location: str,
        size: int,
        local_db_session,
    ):
        asset = AssetModel(
            owner_id=owner.id,
            asset_type_id=asset_type_id,
            name=name,
            file_location=file_location,
            size=size,
        )
        local_db_session.add(asset)
        local_db_session.flush()
        local_db_session.refresh(asset)
        return asset

    def update_asset_permissions(
        self, input: SaveMediaInput, local_db_session, asset: AssetModel
    ):
        if not (len(input.userIds)):
            asset.permissions.delete()
            local_db_session.flush()
            return

        if input.userIds:
            user_ids = input.userIds
            granted_permissions = asset.permissions.all()
            for permission in granted_permissions:
                if isinstance(permission, AssetUsageModel):
                    if (
                        permission.user_id not in user_ids
                        and permission.approved == True
                    ):
                        asset.permissions.remove(permission)
                        local_db_session.delete(permission)
            for user_id in user_ids:
                permission = (
                    local_db_session.query(AssetUsageModel)
                    .filter(
                        AssetUsageModel.asset_id == asset.id,
                        AssetUsageModel.user_id == user_id,
                    )
                    .first()
                )
                if not permission:
                    permission = AssetUsageModel(user_id=user_id)
                    asset.permissions.append(permission)
                permission.approved = True
            local_db_session.flush()

    def process_urls(
        self,
        input: SaveMediaInput,
        local_db_session,
        asset_type: AssetTypeModel,
        asset: AssetModel,
        file_location: str,
    ):
        if input.urls:
            urls = input.urls
            if not asset.description:
                asset.description = "{}"

            attributes = json.loads(asset.description)

            if not "frames" in attributes or attributes["frames"]:
                attributes["frames"] = []

            asset.size = 0
            for url in urls:
                attributes["frames"].append(url)
                full_path = os.path.join(storagePath, url)
                try:
                    size = os.path.getsize(full_path)
                except:
                    size = 0  # file not exist
                asset.size += size

            attributes["multi"] = True if len(urls) > 1 else False
            attributes["frames"] = attributes["frames"] if len(urls) > 1 else []
            attributes["w"] = input.w
            attributes["h"] = input.h
            if asset_type.name == "stream" and "/" not in file_location:
                attributes["isRTMP"] = True

            if input.voice:
                voice = input.voice
                if voice and voice.voice:
                    attributes["voice"] = {
                        "voice": voice.voice,
                        "variant": voice.variant,
                        "pitch": voice.pitch,
                        "speed": voice.speed,
                        "amplitude": voice.amplitude,
                    }
                elif "voice" in attributes:
                    del attributes["voice"]

            if input.link:
                link = input.link
                if link and link.url:
                    attributes["link"] = {
                        "url": link.url,
                        "blank": link.blank,
                        "effect": link.effect,
                    }
                elif "link" in attributes:
                    del attributes["link"]

            attributes["note"] = input.note
            asset.description = json.dumps(attributes)
            local_db_session.flush()
        if not len(input.stageIds):
            asset.stages.delete()

        if len(input.stageIds):
            asset.stages.delete()
            for id in input.stageIds:
                asset.stages.append(
                    ParentStageModel(stage_id=id, child_asset_id=asset.id)
                )

    def change_owner(self, owner: str, local_db_session: ScopedSession, asset: AssetModel):
        if owner:
            new_owner = (
                local_db_session.query(UserModel)
                .filter(UserModel.username == owner)
                .first()
            )
            if new_owner:
                if new_owner.id != asset.owner_id and new_owner.role in (
                    ADMIN,
                    SUPER_ADMIN,
                    PLAYER
                ):
                    asset.owner_id = new_owner.id
            else:
                raise GraphQLError("Owner not found")
        asset.updated_on = datetime.now()
        local_db_session.flush()

    def process_file_location(self, input, local_db_session, asset):
        file_location = input["urls"][0] if "urls" in input else input.urls[0]
        if "?" in file_location:
            file_location = file_location[: file_location.index("?")]
        if file_location != asset.file_location and "/" not in file_location:
            existed_asset = (
                local_db_session.query(AssetModel)
                .filter(AssetModel.file_location == file_location)
                .filter(AssetModel.id != asset.id)
                .first()
            )
            if existed_asset:
                raise GraphQLError(
                    "Stream with the same key already existed, please pick another unique key!"
                )
        asset.file_location = file_location

        return file_location

    def validate_asset_type(self, input, local_db_session):
        media_type = input.mediaType
        asset_type = (
            local_db_session.query(AssetTypeModel)
            .filter(AssetTypeModel.name == media_type)
            .first()
        )

        if not asset_type:
            asset_type = AssetTypeModel(name=media_type, file_location=media_type)
            local_db_session.add(asset_type)
            local_db_session.flush()

        return asset_type

    def delete_media(self, owner: UserModel, id: int):
        with ScopedSession() as local_db_session:
            asset = (
                local_db_session.query(AssetModel)
                .outerjoin(ParentStageModel)
                .filter(AssetModel.id == id)
                .first()
            )

            if not asset:
                raise GraphQLError("Media not found")

            if owner.role not in (ADMIN, SUPER_ADMIN) and owner.id != asset.owner_id:
                return {
                    "success": False,
                    "message": "Only media owner or admin can delete this media!",
                }

            self.cleanup_assets(local_db_session, asset)
            local_db_session.delete(asset)
            local_db_session.flush()

        return {
            "success": True,
            "message": "Media deleted successfully!",
        }

    def update_status(self, owner: UserModel, input: UpdateMediaStatusInput):
        if (input.status.value == MediaStatusEnum.ACTIVE.value) or (
            input.status.value == MediaStatusEnum.DORMANT.value
        ):
            with ScopedSession() as local_db_session:
                asset = (
                    local_db_session.query(AssetModel)
                    .outerjoin(ParentStageModel)
                    .filter(AssetModel.id == input.id)
                    .first()
                )

                if not asset:
                    raise GraphQLError("Media not found")

                asset.dormant = input.status.value == MediaStatusEnum.DORMANT.value
                local_db_session.flush()

                if input.status.value == MediaStatusEnum.ACTIVE.value:
                    # Extract all data needed for async task while asset is still attached to session
                    owner_email = asset.owner.email if asset.owner else None
                    asset_name = asset.name
                    asset_owner_dict = asset.owner.to_dict() if asset.owner else {}
                    asset_dict = asset.to_dict()
                    asset_dict["owner"] = asset_owner_dict
                    if owner_email:
                        asyncio.create_task(
                            send(
                                [owner_email],
                                "Your dormant media item has been reactivated",
                                notify_mark_media_active(asset_dict),
                            )
                        )

            return {
                "success": True,
                "message": "Media updated successfully!",
            }
        return self.delete_media(owner, input.id)

    def cleanup_assets(self, local_db_session, asset: AssetModel):
        if asset.description:
            attributes = json.loads(asset.description)
            if "frames" in attributes:
                for frame in attributes["frames"]:
                    frame_asset = (
                        local_db_session.query(AssetModel)
                        .filter(
                            or_(
                                AssetModel.file_location == frame,
                                AssetModel.description.contains(frame),
                            )
                        )
                        .first()
                    )
                    if not frame_asset:
                        self.file_handing.delete_file(os.path.join(storagePath, frame))

        physical_path = os.path.join(storagePath, asset.file_location)
        local_db_session.query(ParentStageModel).filter(
            ParentStageModel.child_asset_id == asset.id
        ).delete(synchronize_session=False)
        local_db_session.query(MediaTagModel).filter(
            MediaTagModel.asset_id == asset.id
        ).delete(synchronize_session=False)
        local_db_session.query(AssetLicenseModel).filter(
            AssetLicenseModel.asset_id == asset.id
        ).delete(synchronize_session=False)
        local_db_session.query(AssetUsageModel).filter(
            AssetUsageModel.asset_id == asset.id
        ).delete(synchronize_session=False)

        for multiframe_media in (
            local_db_session.query(AssetModel)
            .filter(AssetModel.description.like(f"%{asset.file_location}%"))
            .all()
        ):
            attributes = json.loads(multiframe_media.description)
            for i, frame in enumerate(attributes["frames"]):
                if "?" in frame:
                    attributes["frames"][i] = frame[: frame.index("?")]
            if asset.file_location in attributes["frames"]:
                attributes["frames"].remove(asset.file_location)
            multiframe_media.description = json.dumps(attributes)
            local_db_session.flush()

        self.file_handing.delete_file(physical_path)

    def resolve_sign(self, user: UserModel, asset: AssetModel):
        if asset.owner_id == user.id:
            timestamp = int(
                (datetime.now() + timedelta(days=STREAM_EXPIRY_DAYS)).timestamp()
            )
            payload = "/live/{0}-{1}-{2}".format(
                asset.file_location, timestamp, STREAM_KEY
            )
            hashvalue = hashlib.md5(payload.encode("utf-8")).hexdigest()
            return "{0}-{1}".format(timestamp, hashvalue)
        return ""

    def resolve_sign_from_values(self, owner: UserModel, file_location: str, owner_id: int, user_id: Optional[int]):
        if owner_id == user_id:
            timestamp = int(
                (datetime.now() + timedelta(days=STREAM_EXPIRY_DAYS)).timestamp()
            )
            payload = "/live/{0}-{1}-{2}".format(
                file_location, timestamp, STREAM_KEY
            )
            hashvalue = hashlib.md5(payload.encode("utf-8")).hexdigest()
            return "{0}-{1}".format(timestamp, hashvalue)
        return ""

    def resolve_src(self, asset: AssetModel):
        timestamp = int(time.mktime(asset.updated_on.timetuple()))
        return asset.file_location + "?t=" + str(timestamp)

    def resolve_src_from_values(self, file_location: str, updated_on):
        timestamp = int(time.mktime(updated_on.timetuple()))
        return file_location + "?t=" + str(timestamp)

    def resolve_permission(self, user_id: int, asset: AssetModel):
        if not user_id:
            return "none"
        if asset.owner_id == user_id:
            return "owner"
        if not asset.asset_license or asset.asset_license.level == 0:
            return "editor"
        if asset.asset_license.level == 3:
            return "none"

        player_access = asset.asset_license.permissions if asset.asset_license else None
        if player_access:
            accesses = json.loads(player_access)
            if len(accesses) == 2:
                if user_id in accesses[0]:
                    return "readonly"
                elif user_id in accesses[1]:
                    return "editor"
        return "none"

    def resolve_permission_from_values(self, user_id: int, owner_id: int, asset_license_level: Optional[int], asset_license_permissions: Optional[str], copyright_level: int):
        if not user_id:
            return "none"
        if owner_id == user_id:
            return "owner"
        if asset_license_level is None or asset_license_level == 0:
            return "editor"
        if asset_license_level == 3:
            return "none"

        if asset_license_permissions:
            accesses = json.loads(asset_license_permissions)
            if len(accesses) == 2:
                if user_id in accesses[0]:
                    return "readonly"
                elif user_id in accesses[1]:
                    return "editor"
        return "none"

    def resolve_fields(self, asset: AssetModel, user: Optional[UserModel] = None):
        # Access all data while asset might still be attached to session
        # If asset is detached, we'll reload it in a new session
        from sqlalchemy.orm import object_session
        
        # Extract user.id early to avoid accessing detached user object
        user_id_value = user.id if user else None
        
        session = object_session(asset)
        if session is None:
            # Asset is detached, reload in new session
            with ScopedSession() as local_db_session:
                asset = (
                    local_db_session.query(AssetModel)
                    .options(selectinload(AssetModel.owner))
                    .filter_by(id=asset.id)
                    .first()
                )
                # Extract all data while asset is attached to session
                asset_dict = asset.to_dict()
                # Materialize dynamic relationship by converting to list while session is active
                stages_list = [
                    convert_keys_to_camel_case(item.stage.to_dict())
                    for item in asset.stages.all()  # Use .all() to materialize the dynamic relationship
                ]
                # Extract owner data while session is active
                owner_dict = convert_keys_to_camel_case(asset.owner.to_dict()) if asset.owner else None
                # Extract asset_license values to avoid accessing detached object
                asset_license_level = asset.asset_license.level if asset.asset_license else None
                asset_license_permissions = asset.asset_license.permissions if asset.asset_license else None
                # Extract column values needed for resolve_src and other methods
                updated_on = asset.updated_on
                file_location = asset.file_location
                owner_id = asset.owner_id
                copyright_level = asset.copyright_level
                asset_id = asset.id
        else:
            # Asset is still attached, access relationships now
            asset_dict = asset.to_dict()
            # Materialize dynamic relationship by converting to list while session is active
            stages_list = [
                convert_keys_to_camel_case(item.stage.to_dict())
                for item in asset.stages.all()  # Use .all() to materialize the dynamic relationship
            ]
            # Extract owner data while session is active
            owner_dict = convert_keys_to_camel_case(asset.owner.to_dict()) if asset.owner else None
            # Extract asset_license values to avoid accessing detached object
            asset_license_level = asset.asset_license.level if asset.asset_license else None
            asset_license_permissions = asset.asset_license.permissions if asset.asset_license else None
            # Extract column values needed for resolve_src and other methods
            updated_on = asset.updated_on
            file_location = asset.file_location
            owner_id = asset.owner_id
            copyright_level = asset.copyright_level
            asset_id = asset.id
        
        # Now use extracted values (no relationship access needed)
        src = self.resolve_src_from_values(file_location, updated_on)
        sign = self.resolve_sign_from_values(None, file_location, owner_id, user_id_value)
        effective_user_id = user_id_value if user_id_value else owner_id
        permission = self.resolve_permission_from_values(effective_user_id, owner_id, asset_license_level, asset_license_permissions, copyright_level)
        permissions_list = [
            convert_keys_to_camel_case(permission)
            for permission in self.resolve_permissions(asset_id)
        ]
        
        return {
            **convert_keys_to_camel_case(asset_dict),
            "src": src,
            "sign": sign,
            "permission": permission,
            "privilege": self.resolve_privilege_from_values(user_id_value, owner_id, copyright_level, asset_id),
            "stages": stages_list,
            "permissions": permissions_list,
            "owner": owner_dict,
        }

    def get_media_types(self):
        with ScopedSession() as local_db_session:
            return [
                convert_keys_to_camel_case(type.to_dict())
                for type in local_db_session.query(AssetTypeModel)
                .order_by(AssetTypeModel.name.asc())
                .all()
            ]

    def get_tags(self):
        with ScopedSession() as local_db_session:
            return [
                convert_keys_to_camel_case(tag.to_dict())
                for tag in local_db_session.query(TagModel).order_by(TagModel.name.asc()).all()
            ]

    def get_voices(self):
        with ScopedSession() as local_db_session:
            voices = []
            for media in (
                local_db_session.query(AssetModel)
                .filter(AssetModel.asset_type.has(AssetTypeModel.name == "avatar"))
                .all()
            ):
                if media.description:
                    attributes = json.loads(media.description)
                    if "voice" in attributes:
                        voice = attributes["voice"]
                        if voice and voice["voice"]:
                            av = AvatarVoice()
                            av.voice = voice["voice"]
                            av.variant = voice["variant"]
                            for key in ["pitch", "speed", "amplitude"]:
                                if key in voice:
                                    setattr(av, key, int(voice[key]))
                                else:
                                    if key == "speed":
                                        setattr(av, key, 175)
                                    else:
                                        setattr(av, key, 50)
                            voices.append(Voice(avatar=media, voice=av))
            return [convert_keys_to_camel_case(voice) for voice in voices]

    def resolve_privilege(self, user_id: int, asset: AssetModel):
        if not user_id:
            return Previlege.NONE.value
        if asset.owner_id == user_id:
            return Previlege.OWNER.value
        if not asset.copyright_level:  # no copyright
            return Previlege.APPROVED.value
        if asset.copyright_level == 3:
            return Previlege.NONE.value
        with ScopedSession() as local_db_session:
            usage = (
                local_db_session.query(AssetUsageModel)
                .filter(AssetUsageModel.asset_id == asset.id)
                .filter(AssetUsageModel.user_id == user_id)
                .first()
            )
            if usage:
                if not usage.approved and asset.copyright_level == 2:
                    return Previlege.PENDING_APPROVAL.value
                else:
                    return Previlege.APPROVED.value
            else:
                return Previlege.REQUIRE_APPROVAL.value

    def resolve_privilege_from_values(self, user_id: Optional[int], owner_id: int, copyright_level: int, asset_id: int):
        if not user_id:
            return Previlege.NONE.value
        if owner_id == user_id:
            return Previlege.OWNER.value
        if not copyright_level:  # no copyright
            return Previlege.APPROVED.value
        if copyright_level == 3:
            return Previlege.NONE.value
        with ScopedSession() as local_db_session:
            usage = (
                local_db_session.query(AssetUsageModel)
                .filter(AssetUsageModel.asset_id == asset_id)
                .filter(AssetUsageModel.user_id == user_id)
                .first()
            )
            if usage:
                if not usage.approved and copyright_level == 2:
                    return Previlege.PENDING_APPROVAL.value
                else:
                    return Previlege.APPROVED.value
            else:
                return Previlege.REQUIRE_APPROVAL.value

    def resolve_permissions(self, asset_id: int):
        with ScopedSession() as local_db_session:
            permissions = (
                local_db_session.query(AssetUsageModel)
                .filter(AssetUsageModel.asset_id == asset_id)
                .order_by(AssetUsageModel.created_on.desc())
                .all()
            )
            # Convert to dicts while objects are still attached to session
            return [permission.to_dict() for permission in permissions]
