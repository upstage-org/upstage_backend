import asyncio
import os

from datetime import datetime, timedelta
import hashlib
import json
import re
from typing import Optional
import time
from graphql import GraphQLError
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload


from upstage_backend.global_config import get_session
from upstage_backend.global_config.env import (
    UPLOAD_USER_CONTENT_FOLDER,
    STREAM_EXPIRY_DAYS,
    STREAM_KEY,
)
from upstage_backend.global_config.helpers.authz import is_admin, require_owner_or_admin
from upstage_backend.global_config.helpers.background import spawn
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.global_config.helpers.paths import (
    is_safe_relative_path,
    safe_join,
    try_safe_join,
)
from upstage_backend.assets.db_models.asset import (
    AssetModel,
    AvatarVoice,
    Voice,
    Previlege,
)
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
from upstage_backend.assets.db_models.asset_type import AssetTypeModel
from upstage_backend.assets.db_models.asset_usage import AssetUsageModel
from upstage_backend.assets.db_models.media_tag import MediaTagModel
from upstage_backend.assets.db_models.tag import TagModel
from upstage_backend.assets.http.validation import (
    MediaTableInput,
    SaveMediaInput,
    UpdateMediaStatusInput,
    MediaStatusEnum,
)
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.services.assignment import sync_asset_assignments
from upstage_backend.users.db_models.user import ADMIN, PLAYER, SUPER_ADMIN, UserModel
from upstage_backend.users.services.upload_limit import enforce_upload_cap
from upstage_backend.files.file_handling import FileHandling
from upstage_backend.files.video_poster import extract_first_frame
from upstage_backend.mails.helpers.mail import send
from upstage_backend.mails.templates.templates import notify_mark_media_active


storagePath = UPLOAD_USER_CONTENT_FOLDER


# A MediaMTX playback origin as the frontend lists it in VITE_RTMP_ENDPOINTS:
# scheme + host (+ optional port), nothing else. The value is used verbatim to
# build WHEP/HLS URLs and the OBS ingest URL, so reject anything with a path,
# query, credentials or a non-http scheme.
_RTMP_ENDPOINT_RE = re.compile(r"^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$")

# A media type doubles as the upload sub-folder (AssetTypeModel.file_location),
# so it must be a single plain path component: no separators, dots or blanks.
_MEDIA_TYPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def normalise_rtmp_endpoint(value: str) -> str:
    candidate = (value or "").strip().rstrip("/")
    if not _RTMP_ENDPOINT_RE.match(candidate):
        raise GraphQLError("Invalid streaming server: expected https://host[:port]")
    return candidate


class AssetService:
    def __init__(self):
        self.file_handing = FileHandling()
        pass

    # Relationships AssetModel.to_dict() walks for every listed asset; one
    # SELECT ... IN each for the whole result instead of three lazy loads per row.
    _ASSET_EAGER = (
        selectinload(AssetModel.asset_type),
        selectinload(AssetModel.owner),
        selectinload(AssetModel.asset_license),
    )

    def _prefetch_asset_relations(self, session, assets):
        """
        Bulk-load, for a list of assets, everything resolve_fields() and the
        media table edges read per asset: stage assignments (with the stage
        and its owner), usage/permission rows (with their user) and tag
        names. Three queries for the page instead of ~5 per asset.
        """
        ids = [asset.id for asset in assets]
        stages, usages, tags = {}, {}, {}
        if not ids:
            return {"stages": stages, "usages": usages, "tags": tags}
        for row in (
            session.query(ParentStageModel)
            .filter(ParentStageModel.child_asset_id.in_(ids))
            .options(joinedload(ParentStageModel.stage).joinedload(StageModel.owner))
            .order_by(ParentStageModel.id)
            .all()
        ):
            stages.setdefault(row.child_asset_id, []).append(row)
        for row in (
            session.query(AssetUsageModel)
            .filter(AssetUsageModel.asset_id.in_(ids))
            .options(joinedload(AssetUsageModel.user), joinedload(AssetUsageModel.asset))
            .order_by(AssetUsageModel.created_on.desc())
            .all()
        ):
            usages.setdefault(row.asset_id, []).append(row)
        for asset_id, name in (
            session.query(MediaTagModel.asset_id, TagModel.name)
            .join(TagModel, MediaTagModel.tag_id == TagModel.id)
            .filter(MediaTagModel.asset_id.in_(ids))
            .order_by(MediaTagModel.id)
            .all()
        ):
            if name:
                tags.setdefault(asset_id, []).append(name)
        return {"stages": stages, "usages": usages, "tags": tags}

    def get_all_medias(self, user: UserModel, filter: dict | None = None):
        filter = filter or {}
        session = get_session()
        query = (
            session.query(AssetModel)
            .join(AssetTypeModel)
            .join(UserModel)
            .outerjoin(AssetLicenseModel)
            .outerjoin(ParentStageModel, AssetModel.id == ParentStageModel.child_asset_id)
            # Was `ParentStageModel.stage_id == AssetModel.id`: a stage joined
            # to an unrelated asset whenever the ids happened to coincide.
            .outerjoin(StageModel, ParentStageModel.stage_id == StageModel.id)
            .filter(AssetModel.dormant.is_not(True))
            .order_by(AssetModel.created_on.desc())
            .options(*self._ASSET_EAGER)
        )

        if "mediaType" in filter:
            query = query.filter(AssetTypeModel.name == filter["mediaType"])

        if "owner" in filter:
            query = query.filter(UserModel.username == filter["owner"])

        assets = query.all()
        prefetched = self._prefetch_asset_relations(session, assets)

        return [self.resolve_fields(asset, user, prefetched) for asset in assets]

    def search_assets(self, user: UserModel, search_assets: MediaTableInput):
        session = get_session()
        query = (
            session.query(AssetModel)
            .join(UserModel)
            .join(AssetTypeModel)
            .outerjoin(AssetLicenseModel)
            .outerjoin(ParentStageModel, AssetModel.id == ParentStageModel.child_asset_id)
            .outerjoin(StageModel, ParentStageModel.stage_id == StageModel.id)
            .group_by(AssetModel.id)
            .options(*self._ASSET_EAGER)
        )

        if user.role not in [SUPER_ADMIN, ADMIN]:
            query = query.filter(AssetModel.dormant.is_not(True))
        elif search_assets.dormant is not None:
            query = query.filter(AssetModel.dormant.is_(search_assets.dormant))

        if search_assets.name:
            # The search box matches media name, tags, and the note/attributes
            # blob (stored inside the `description` column). Previously only the
            # `name` column was searched, so an avatar the author knows by a tag
            # or note — but whose stored name is the raw uploaded filename —
            # would not surface (e.g. searching "helen" when "helen" is a tag).
            term = f"%{search_assets.name}%"
            tag_matches = (
                session.query(MediaTagModel.asset_id)
                .join(TagModel, MediaTagModel.tag_id == TagModel.id)
                .filter(TagModel.name.ilike(term))
            )
            query = query.filter(
                AssetModel.name.ilike(term)
                | AssetModel.description.ilike(term)
                | AssetModel.id.in_(tag_matches)
            )
        if search_assets.mediaTypes:
            query = query.filter(AssetTypeModel.name.in_(search_assets.mediaTypes))
        if search_assets.owners:
            query = query.filter(UserModel.username.in_(search_assets.owners))

        if search_assets.stages:
            query = query.filter(
                AssetModel.stages.any(ParentStageModel.stage_id.in_(search_assets.stages))
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
            # The table sends an ordered list of sort keys for multi-column
            # sorting (e.g. ["OWNER_ID_ASC", "NAME_ASC"]). Apply every one in
            # priority order — previously only the last entry (`sort[-1]`) was
            # honoured, so multi-column sort silently did nothing beyond one
            # column. Unknown/blank keys (e.g. a cleared column) are skipped
            # rather than raising an UnboundLocalError.
            sort_field_map = {
                "ASSET_TYPE_ID": AssetModel.asset_type_id,
                "OWNER_ID": AssetModel.owner_id,
                "NAME": AssetModel.name,
                "CREATED_ON": AssetModel.created_on,
                "SIZE": AssetModel.size,
                "COPYRIGHT_LEVEL": AssetModel.copyright_level,
            }
            for sort_option in search_assets.sort:
                field, _, direction = sort_option.rpartition("_")
                sort_field = sort_field_map.get(field)
                if sort_field is None:
                    continue
                query = query.order_by(
                    sort_field.asc() if direction == "ASC" else sort_field.desc()
                )

        if search_assets.page and search_assets.limit:
            query = query.limit(search_assets.limit).offset(
                (search_assets.page - 1) * search_assets.limit
            )
        assets = query.all()
        prefetched = self._prefetch_asset_relations(session, assets)

        return {
            "totalCount": total_count,
            "edges": [
                {
                    **convert_keys_to_camel_case(asset.to_dict()),
                    "privilege": self.resolve_privilege(
                        user.id, asset, usages=prefetched["usages"].get(asset.id, [])
                    ),
                    "stages": [
                        convert_keys_to_camel_case(item.stage.to_dict())
                        for item in prefetched["stages"].get(asset.id, [])
                    ],
                    "permissions": [
                        convert_keys_to_camel_case(permission.to_dict())
                        for permission in prefetched["usages"].get(asset.id, [])
                    ],
                    "tags": prefetched["tags"].get(asset.id, []),
                }
                for asset in assets
            ],
        }

    # File extensions that FileHandling.validate_file_size treats as
    # videos. Kept in sync manually because that method bakes the
    # allowlist into an `if/elif` chain rather than exposing it. If
    # a new format is added there, add it here too so posters get
    # generated for it.
    _VIDEO_EXTENSIONS = (".mp4", ".webm", ".opgg", ".3gp", ".flv")

    async def upload_file_async(self, user: UserModel, base64: str, filename: str):
        """upload_file without stalling the server.

        The upload path is pure blocking work: a base64 decode of the whole
        payload, a disk write, and for videos a synchronous ffmpeg run that
        may take up to its 30 s timeout. On the event loop that froze every
        other request for the duration. It touches no database session, so
        it is safe to run in a worker thread.
        """
        return await asyncio.to_thread(self.upload_file, user, base64, filename)

    def upload_file(self, user: UserModel, base64: str, filename: str):
        file_size = self.file_handing.get_file_size(base64)

        # Per-user cap policy lives in users.services.upload_limit (admins
        # exempt, NULL = 1 MiB default); the global per-extension caps in
        # FileHandling.validate_file_size still apply on the write.
        enforce_upload_cap(user.role, user.upload_limit, file_size)

        file_location = self.file_handing.upload_file(base64, filename, None, storagePath, "media")

        # Poster generation is best-effort and synchronous: the file
        # is small (one JPEG) and ffmpeg's first-frame extraction is
        # quick relative to the upload round-trip. If anything goes
        # wrong (ffmpeg missing, corrupt video, timeout) we log and
        # return the original location anyway — the frontend gracefully
        # degrades to "no poster" for that asset.
        _, ext = os.path.splitext(filename)
        if ext.lower() in self._VIDEO_EXTENSIONS:
            abs_video_path = os.path.join(storagePath, file_location)
            extract_first_frame(abs_video_path)

        return {"url": file_location}

    def save_media(self, owner: UserModel, input: SaveMediaInput):
        session = get_session()
        asset_type = self.validate_asset_type(input, session)

        if input.id:
            asset = session.query(AssetModel).filter(AssetModel.id == input.id).first()
            if not asset:
                raise GraphQLError("Media not found")
            require_owner_or_admin(owner, asset.owner_id, "You are not allowed to update this asset")
        else:
            asset = AssetModel(owner_id=owner.id)
        # Stage links are rebuilt from input.stageAssignments below; reject the
        # request before any write if it names a stage the caller cannot use.
        self.assert_can_assign_to_stages(
            owner, [assignment.stageId for assignment in input.stageAssignments or []], session
        )

        # Validate + assign file_location BEFORE mutating the asset or adding
        # it to the session. GraphQL errors return HTTP 200, so anything left
        # pending here gets committed by the db_request_session middleware:
        # previously a duplicate-key rejection left a half-built row (NULL
        # file_location) that crashed that commit, and on edits it silently
        # committed partial name/copyright changes.
        file_location = self.process_file_location(input, session, asset)
        # Same rule for the RTMP server binding: validate before the asset is
        # pending so a malformed value cannot leave a half-built row behind.
        rtmp_endpoint = normalise_rtmp_endpoint(input.rtmpEndpoint) if input.rtmpEndpoint else None
        if not input.id:
            session.add(asset)

        asset.name = input.name
        asset.asset_type_id = asset_type.id
        asset.copyright_level = input.copyrightLevel

        self.change_owner(input.owner, session, asset)

        self.process_urls(input, session, asset_type, asset, file_location, rtmp_endpoint)

        self.update_asset_permissions(input, session, asset)
        asset = self.update_asset_tags(input, session, asset)
        session.flush()

        return convert_keys_to_camel_case({"asset": {"id": asset.id}})

    def update_asset_tags(self, input: SaveMediaInput, local_db_session, asset: AssetModel):
        if input.tags:
            tags = input.tags
            asset.tags.delete()
            for tag in tags:
                tag_model = local_db_session.query(TagModel).filter(TagModel.name == tag).first()
                if not tag_model:
                    tag_model = TagModel(name=tag)
                    local_db_session.add(tag_model)
                    local_db_session.flush()
                asset.tags.append(MediaTagModel(tag_id=tag_model.id))

            local_db_session.flush()
            asset = local_db_session.query(AssetModel).filter(AssetModel.id == asset.id).first()

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

    def update_asset_permissions(self, input: SaveMediaInput, local_db_session, asset: AssetModel):
        if not (len(input.userIds)):
            asset.permissions.delete()
            local_db_session.flush()
            return

        if input.userIds:
            user_ids = input.userIds
            granted_permissions = asset.permissions.all()
            for permission in granted_permissions:
                if isinstance(permission, AssetUsageModel):
                    if permission.user_id not in user_ids and permission.approved:
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
        rtmp_endpoint: Optional[str] = None,
    ):
        # Voice / link / note used to be nested inside `if input.urls:`, which
        # meant clicking Save on the Voice tab (or Link tab) without uploading
        # new frames silently discarded those edits. Persist the attribute
        # JSON whenever any of url/voice/link/note input fields are provided.
        attribute_update = (
            bool(input.urls)
            or input.voice is not None
            or input.link is not None
            or input.note is not None
        )
        if attribute_update:
            if not asset.description:
                asset.description = "{}"

            attributes = json.loads(asset.description)

            if input.urls:
                urls = input.urls
                if "frames" not in attributes or attributes["frames"]:
                    attributes["frames"] = []

                asset.size = 0
                for url in urls:
                    # Frame locations are user input and are later joined onto
                    # the uploads root for reads and deletes: confine them now.
                    if not is_safe_relative_path(url):
                        raise GraphQLError("Invalid file location")
                    attributes["frames"].append(url)
                    full_path = safe_join(storagePath, url)
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        size = 0  # file not exist
                    asset.size += size

                attributes["multi"] = True if len(urls) > 1 else False
                attributes["frames"] = attributes["frames"] if len(urls) > 1 else []
                attributes["w"] = input.w
                attributes["h"] = input.h
                if asset_type.name == "stream" and "/" not in file_location:
                    attributes["isRTMP"] = True
                    # Multi-server streaming: pin the feed to one MediaMTX.
                    # Absent ⇒ keep whatever the blob already had (legacy
                    # feeds have nothing and resolve to the default server).
                    if rtmp_endpoint:
                        attributes["rtmpEndpoint"] = rtmp_endpoint

            if input.voice is not None:
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

            if input.link is not None:
                link = input.link
                if link and link.url:
                    attributes["link"] = {
                        "url": link.url,
                        "blank": link.blank,
                        "effect": link.effect,
                    }
                elif "link" in attributes:
                    del attributes["link"]

            if input.note is not None:
                attributes["note"] = input.note

            asset.description = json.dumps(attributes)
            local_db_session.flush()

        # Rebuild the stage assignments. Exit settings live per assignment;
        # explicit values win, otherwise a pair that survives the rebuild
        # keeps the settings it already had.
        # Surviving assignments also keep their parent_stage ROW, i.e. their
        # place in each stage's saved media order — re-saving a media item
        # used to send it to the end of every stage it was on (see
        # sync_asset_assignments).
        if asset.id is None:
            # Brand-new asset whose INSERT has not been flushed yet.
            local_db_session.flush()
        sync_asset_assignments(
            local_db_session,
            asset.id,
            [
                (assignment.stageId, assignment.exitAnimation, assignment.exitSpeed)
                for assignment in input.stageAssignments
            ],
        )

    def assert_can_assign_to_stages(self, user, stage_ids, local_db_session) -> None:
        """
        A media owner may attach media to a stage they own, edit, or have
        been granted player access to (playerAccess lists); admins anywhere.
        Previously any authenticated user could link media to any stage.
        """
        wanted = {int(stage_id) for stage_id in (stage_ids or []) if stage_id is not None}
        if not wanted or is_admin(user):
            return
        from upstage_backend.stages.services.stage_operation import StageOperationService

        resolve_permission = StageOperationService().resolve_permission
        stages = local_db_session.query(StageModel).filter(StageModel.id.in_(wanted)).all()
        for stage in stages:
            if resolve_permission(user.id, stage) not in ("owner", "editor", "player"):
                raise GraphQLError(
                    f'You do not have access to stage "{stage.name}" and cannot assign media to it'
                )

    def change_owner(self, owner: str, local_db_session, asset: AssetModel):
        if owner:
            new_owner = (
                local_db_session.query(UserModel).filter(UserModel.username == owner).first()
            )
            if new_owner:
                if new_owner.id != asset.owner_id and new_owner.role in (
                    ADMIN,
                    SUPER_ADMIN,
                    PLAYER,
                ):
                    asset.owner_id = new_owner.id
            else:
                raise GraphQLError("Owner not found")
        asset.updated_on = datetime.now()
        local_db_session.flush()

    def process_file_location(self, input, local_db_session, asset):
        # Called with a SaveMediaInput (saveMedia) or a plain dict (updateMedia).
        urls = input["urls"] if isinstance(input, dict) else input.urls
        if not urls:
            # Saving an attribute-only edit (voice/link/note) resends no
            # frames; keep the existing file. A brand-new asset has no file
            # to fall back to and the column is NOT NULL.
            if not asset.file_location:
                raise GraphQLError("A media file is required")
            return asset.file_location
        file_location = urls[0]
        if not isinstance(file_location, str):
            raise GraphQLError("Invalid file location")
        if "?" in file_location:
            file_location = file_location[: file_location.index("?")]
        # The value is joined onto the uploads root for every later read,
        # write and delete of this asset: refuse anything that could escape it.
        if not is_safe_relative_path(file_location):
            raise GraphQLError("Invalid file location")
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
        if not isinstance(media_type, str) or not _MEDIA_TYPE_RE.match(media_type):
            raise GraphQLError("Unsupported media type")
        asset_type = (
            local_db_session.query(AssetTypeModel).filter(AssetTypeModel.name == media_type).first()
        )

        if not asset_type:
            asset_type = AssetTypeModel(name=media_type, file_location=media_type)
            local_db_session.add(asset_type)
            local_db_session.flush()

        return asset_type

    def delete_media(self, owner: UserModel, id: int):
        session = get_session()
        asset = (
            session.query(AssetModel)
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

        self.cleanup_assets(session, asset)
        session.delete(asset)
        session.flush()

        return {
            "success": True,
            "message": "Media deleted successfully!",
        }

    def update_status(self, owner: UserModel, input: UpdateMediaStatusInput):
        if (input.status.value == MediaStatusEnum.ACTIVE.value) or (
            input.status.value == MediaStatusEnum.DORMANT.value
        ):
            session = get_session()
            asset = (
                session.query(AssetModel)
                .outerjoin(ParentStageModel)
                .filter(AssetModel.id == input.id)
                .first()
            )

            if not asset:
                raise GraphQLError("Media not found")
            require_owner_or_admin(
                owner, asset.owner_id, "Only media owner or admin can update this media!"
            )

            asset.dormant = input.status.value == MediaStatusEnum.DORMANT.value
            session.flush()

            if input.status.value == MediaStatusEnum.ACTIVE.value:
                spawn(
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
                        self.file_handing.delete_file(try_safe_join(storagePath, frame))

        physical_path = try_safe_join(storagePath, asset.file_location or "")
        local_db_session.query(ParentStageModel).filter(
            ParentStageModel.child_asset_id == asset.id
        ).delete(synchronize_session=False)
        local_db_session.query(MediaTagModel).filter(MediaTagModel.asset_id == asset.id).delete(
            synchronize_session=False
        )
        local_db_session.query(AssetLicenseModel).filter(
            AssetLicenseModel.asset_id == asset.id
        ).delete(synchronize_session=False)
        local_db_session.query(AssetUsageModel).filter(AssetUsageModel.asset_id == asset.id).delete(
            synchronize_session=False
        )

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
            timestamp = int((datetime.now() + timedelta(days=STREAM_EXPIRY_DAYS)).timestamp())
            payload = "/live/{0}-{1}-{2}".format(asset.file_location, timestamp, STREAM_KEY)
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

    @staticmethod
    def _tag_names_for_asset(asset: AssetModel) -> list[str]:
        """
        ``AssetModel.tags`` is a dynamic relationship; ``BaseModel.to_dict`` does
        not expand it into tag names. GraphQL exposes ``tags: [String]``.
        """
        names: list[str] = []
        for media_tag in asset.tags:
            tag = media_tag.tag
            if tag is not None and tag.name:
                names.append(tag.name)
        return names

    def resolve_fields(self, asset: AssetModel, user: Optional[UserModel] = None, prefetched=None):
        """
        `prefetched` (from _prefetch_asset_relations) supplies the stage
        assignments, usage rows and tag names for list responses; single-asset
        callers leave it None and the relationships are read per asset.
        """
        src = self.resolve_src(asset)
        # Publish token: only meaningful (and only revealed) to the asset's
        # owner. resolve_sign returns "" for anyone else.
        sign = self.resolve_sign(user, asset) if user else ""
        user_id = user.id if user else asset.owner_id
        permission = self.resolve_permission(user_id, asset)
        if prefetched is not None:
            stage_links = prefetched["stages"].get(asset.id, [])
            usages = prefetched["usages"].get(asset.id, [])
            tags = prefetched["tags"].get(asset.id, [])
        else:
            stage_links = asset.stages
            usages = self.resolve_permissions(asset.id)
            tags = self._tag_names_for_asset(asset)
        return {
            **convert_keys_to_camel_case(asset.to_dict()),
            "src": src,
            "sign": sign,
            "permission": permission,
            "privilege": self.resolve_privilege(
                user.id if user else None, asset, usages=usages if prefetched is not None else None
            ),
            "stages": [
                {
                    **convert_keys_to_camel_case(item.stage.to_dict()),
                    "exitAnimation": item.exit_animation,
                    "exitSpeed": item.exit_speed,
                }
                for item in stage_links
            ],
            "permissions": [convert_keys_to_camel_case(usage.to_dict()) for usage in usages],
            "tags": tags,
        }

    def get_media_types(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(type.to_dict())
            for type in session.query(AssetTypeModel).order_by(AssetTypeModel.name.asc()).all()
        ]

    def get_tags(self):
        session = get_session()
        return [
            convert_keys_to_camel_case(tag.to_dict())
            for tag in session.query(TagModel).order_by(TagModel.name.asc()).all()
        ]

    def get_voices(self):
        session = get_session()
        voices = []
        for media in (
            session.query(AssetModel)
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

    def resolve_privilege(self, user_id: int, asset: AssetModel, usages=None):
        """`usages`: this asset's AssetUsageModel rows when the caller already
        loaded them in bulk; otherwise the caller's row is looked up here."""
        if not user_id:
            return Previlege.NONE.value
        if asset.owner_id == user_id:
            return Previlege.OWNER.value
        if not asset.copyright_level:  # no copyright
            return Previlege.APPROVED.value
        if asset.copyright_level == 3:
            return Previlege.NONE.value
        if usages is not None:
            usage = next((u for u in usages if u.user_id == user_id), None)
        else:
            session = get_session()
            usage = (
                session.query(AssetUsageModel)
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
        session = get_session()
        return (
            session.query(AssetUsageModel)
            .filter(AssetUsageModel.asset_id == asset_id)
            .order_by(AssetUsageModel.created_on.desc())
            .all()
        )
