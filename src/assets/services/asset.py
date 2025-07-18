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


from global_config import (
    ScopedSession,
    DBSession,
    UPLOAD_USER_CONTENT_FOLDER,
    STREAM_EXPIRY_DAYS,
    STREAM_KEY,
    convert_keys_to_camel_case,
)
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
        query = (
            DBSession.query(AssetModel)
            .join(AssetTypeModel)
            .join(UserModel)
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

        return [self.resolve_fields(asset, user) for asset in assets]

    def search_assets(self, user: UserModel, search_assets: MediaTableInput):
        query = (
            DBSession.query(AssetModel)
            .join(UserModel)
            .join(AssetTypeModel)
            .outerjoin(AssetLicenseModel)
            .outerjoin(
                ParentStageModel, AssetModel.id == ParentStageModel.child_asset_id
            )
            .outerjoin(StageModel, ParentStageModel.stage_id == AssetModel.id)
            .group_by(AssetModel.id)
        )

        if user.role not in [SUPER_ADMIN, ADMIN]:
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

        return {
            "totalCount": total_count,
            "edges": [
                {
                    **convert_keys_to_camel_case(asset.to_dict()),
                    "privilege": self.resolve_privilege(user.id, asset),
                    "stages": [
                        convert_keys_to_camel_case(item.stage.to_dict())
                        for item in asset.stages
                    ],
                    "permissions": [
                        convert_keys_to_camel_case(permission.to_dict())
                        for permission in self.resolve_permissions(asset.id)
                    ],
                }
                for asset in assets
            ],
        }

    def upload_file(self, user: UserModel, base64: str, filename: str):
        file_size = self.file_handing.get_file_size(base64)

        if file_size > user.upload_limit:
            raise GraphQLError(
                f"File size must be under {self.file_handing.convert_KB_to_MB(user.upload_limit)}MB."
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
                    asyncio.create_task(
                        send(
                            [asset.owner.email],
                            "Your dormant media item has been reactivated",
                            notify_mark_media_active(asset),
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

    def resolve_src(self, asset: AssetModel):
        timestamp = int(time.mktime(asset.updated_on.timetuple()))
        return asset.file_location + "?t=" + str(timestamp)

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

    def resolve_fields(self, asset: AssetModel, user: Optional[UserModel] = None):
        src = self.resolve_src(asset)
        sign = self.resolve_sign(asset.owner, asset)
        user_id = user.id if user else asset.owner_id
        permission = self.resolve_permission(user_id, asset)
        return {
            **convert_keys_to_camel_case(asset.to_dict()),
            "src": src,
            "sign": sign,
            "permission": permission,
            "privilege": self.resolve_privilege(user.id if user else None, asset),
            "stages": [
                convert_keys_to_camel_case(item.stage.to_dict())
                for item in asset.stages
            ],
            "permissions": [
                convert_keys_to_camel_case(permission.to_dict())
                for permission in self.resolve_permissions(asset.id)
            ],
        }

    def get_media_types(self):
        return [
            convert_keys_to_camel_case(type.to_dict())
            for type in DBSession.query(AssetTypeModel)
            .order_by(AssetTypeModel.name.asc())
            .all()
        ]

    def get_tags(self):
        return [
            convert_keys_to_camel_case(tag.to_dict())
            for tag in DBSession.query(TagModel).order_by(TagModel.name.asc()).all()
        ]

    def get_voices(self):
        voices = []
        for media in (
            DBSession.query(AssetModel)
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
        usage = (
            DBSession.query(AssetUsageModel)
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

    def resolve_permissions(self, asset_id: int):
        return (
            DBSession.query(AssetUsageModel)
            .filter(AssetUsageModel.asset_id == asset_id)
            .order_by(AssetUsageModel.created_on.desc())
            .all()
        )
