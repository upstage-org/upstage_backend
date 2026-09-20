# -*- coding: iso8859-15 -*-
import asyncio
import os

import json
import uuid
from graphql import GraphQLError
from sqlalchemy import and_, or_
from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
from upstage_backend.assets.db_models.asset_usage import AssetUsageModel
from upstage_backend.assets.db_models.media_tag import MediaTagModel
from upstage_backend.assets.services.asset import AssetService
from upstage_backend.assets.services.asset_license import AssetLicenseService
from upstage_backend.global_config import get_session
from upstage_backend.global_config.db_context import finish_request_transaction
from upstage_backend.global_config.env import UPLOAD_USER_CONTENT_FOLDER
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.files.file_handling import FileHandling
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.services.assignment import (
    make_parent_stage,
    snapshot_exit_settings,
    sync_asset_assignments,
)
from upstage_backend.stages.http.validation import (
    AssignMediaInput,
    AssignStagesInput,
    UpdateMediaInput,
    UpdateStageAssignmentInput,
    UploadMediaInput,
)
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN, UserModel
from upstage_backend.users.services.upload_limit import enforce_upload_cap

storagePath = UPLOAD_USER_CONTENT_FOLDER


class MediaService:
    def __init__(self):
        self.asset_service = AssetService()
        self.asset_license_service = AssetLicenseService()
        self.file_handling = FileHandling()

    def assign_media(self, input: AssignMediaInput, user: UserModel):
        session = get_session()
        stage = session.query(StageModel).filter_by(id=input.id).first()
        if not stage or not input.id:
            raise GraphQLError("Stage not found")

        if stage.owner_id != user.id and user.role not in [ADMIN, SUPER_ADMIN]:
            raise GraphQLError("You are not authorized to update this stage")

        snapshot = snapshot_exit_settings(session, stage_id=input.id)
        session.query(ParentStageModel).filter(ParentStageModel.stage_id == input.id).delete()

        for media_id in input.mediaIds:
            session.add(make_parent_stage(input.id, media_id, snapshot))

        session.flush()
        return convert_keys_to_camel_case(stage.to_dict())

    # Event-loop rules for the two upload mutations below. Resolvers run on
    # the uvicorn event loop, so decoding a multi-megabyte base64 payload and
    # writing it to disk there froze every other request. That work now runs
    # in a worker thread, under two constraints:
    #   * the thread never touches the SQLAlchemy session (not thread-safe);
    #   * no flushed write may be pending when we ``await``: a row lock held
    #     while other requests get the loop is the 2026-09-19 outage. So all
    #     file IO happens BEFORE the first write that takes a lock, and the
    #     one write that can precede it (validate_asset_type inserting a
    #     brand-new asset type) is committed first.

    async def upload_media(self, user: UserModel, input: UploadMediaInput):
        # Same per-user cap as AssetService.upload_file, checked before any
        # lookup or write: this mutation used to skip it entirely
        # (2026-09-11).
        size = await asyncio.to_thread(self.file_handling.get_file_size, input.base64)
        enforce_upload_cap(user.role, user.upload_limit, size)

        session = get_session()
        asset_type = self.asset_service.validate_asset_type(input, session)
        finish_request_transaction(commit=True)
        file_location = await asyncio.to_thread(
            self.file_handling.upload_file,
            base64=input.base64,
            file_name=input.filename,
            absolute_path=None,
            storage_path=storagePath,
            sub_path=asset_type.file_location,
        )

        asset = self.asset_service.create_asset(
            owner=user,
            asset_type_id=asset_type.id,
            name=input.name,
            file_location=file_location,
            size=size,
            local_db_session=session,
        )

        return self.asset_service.resolve_fields(asset, user)

    async def update_media(self, input: UpdateMediaInput, user: UserModel):
        # Cap the replacement file and every uploaded frame BEFORE any
        # lookup, write or mutation, so an over-limit frame cannot leave a
        # half-updated asset behind. Neither path was capped before
        # (2026-09-11).
        for payload in [input.base64, *(input.uploadedFrames or [])]:
            if payload:
                enforce_upload_cap(
                    user.role,
                    user.upload_limit,
                    await asyncio.to_thread(self.file_handling.get_file_size, payload),
                )

        session = get_session()
        asset_type = self.asset_service.validate_asset_type(input, session)
        # Nothing else is pending yet, so this commits at most a new asset type.
        finish_request_transaction(commit=True)

        asset = self.retrieve_asset(input, session)
        asset.name = input.name
        asset.asset_type_id = asset_type.id
        asset.description = input.description

        file_location = self.asset_service.process_file_location(
            {"urls": [input.fileLocation]}, session, asset
        )
        asset.file_location = file_location

        # Everything above is reads plus unflushed in-memory changes
        # (autoflush is off), so no row lock is held across this await.
        frames_sub_path = asset_type.file_location
        processed_description, frame_jobs = self.plan_uploaded_frames(input, asset, frames_sub_path)
        replacement_path = os.path.join(storagePath, asset.file_location)

        def _write_files():
            if input.base64:
                self.file_handling.write_file(base64=input.base64, path=replacement_path)
            for frame, filename in frame_jobs:
                self.file_handling.upload_file(
                    base64=frame,
                    file_name=filename,
                    absolute_path=None,
                    storage_path=storagePath,
                    sub_path=frames_sub_path,
                )

        if input.base64 or frame_jobs:
            await asyncio.to_thread(_write_files)

        self.asset_license_service.create(
            asset_id=asset.id,
            player_access=input.playerAccess,
            local_db_session=session,
            copyright_level=input.copyrightLevel,
        )
        # plan_uploaded_frames yields None when input.uploadedFrames is
        # falsy; assigning that back would wipe asset.description (and any
        # saved voice/link/note attributes) on every non-frame edit.
        if processed_description is not None:
            asset.description = processed_description
        session.flush()
        asset = session.query(AssetModel).filter_by(id=asset.id).first()
        return self.asset_service.resolve_fields(asset)

    def retrieve_asset(self, input, local_db_session):
        if input.id:
            asset = local_db_session.query(AssetModel).filter_by(id=input.id).first()
            if not asset:
                raise GraphQLError("Media not found")

        if input.fileLocation:
            existed_asset = (
                local_db_session.query(AssetModel)
                .filter(
                    and_(
                        AssetModel.file_location == input.fileLocation,
                        AssetModel.id != input.id,
                    )
                )
                .first()
            )
            if existed_asset:
                raise GraphQLError("Media with the same key already existed, please pick another!")

        return asset

    def plan_uploaded_frames(self, input: UpdateMediaInput, asset: AssetModel, sub_path: str):
        """Session-side half of multiframe uploads: pick the frame filenames
        and build the new description, without touching the disk.

        Returns ``(description_json | None, [(frame_base64, filename), ...])``;
        the caller writes the files in a worker thread. Filenames and the
        recorded locations are computed exactly as before the split.
        """
        if not input.uploadedFrames:
            return None, []

        _, file_extension = os.path.splitext(asset.file_location)
        attributes = json.loads(asset.description)
        if "frames" not in attributes:
            attributes["frames"] = []

        jobs = []
        for frame in input.uploadedFrames:
            filename = uuid.uuid4().hex + file_extension
            jobs.append((frame, filename))
            attributes["frames"].append(os.path.join(sub_path, filename))

        return json.dumps(attributes), jobs

    def delete_media(self, id: int):
        session = get_session()
        asset = session.query(AssetModel).outerjoin(ParentStageModel).filter_by(id=id).first()
        if not asset:
            raise GraphQLError("Media not found")

        if asset.stages:
            asset.dormant = True
            session.flush()
            return

        physical_path = self.remove_media_frames_and_get_path(session, asset)

        self.file_handling.delete_file(physical_path)

        self.cleanup_related_entities(id, session)
        self.remove_asset_from_frames(session, asset)
        session.delete(asset)
        session.flush()

        return {"success": True, "message": "Media deleted successfully"}

    def remove_media_frames_and_get_path(self, local_db_session, asset):
        if asset.description:
            attributes = json.loads(asset.description)
            if "frames" in attributes and attributes["frames"]:
                self._delete_frames(local_db_session, attributes["frames"])
        return self._get_physical_path(asset.file_location)

    def _delete_frames(self, local_db_session, frames):
        for frame in frames:
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
                self.file_handling.delete_file(os.path.join(storagePath, frame))

    def _get_physical_path(self, file_location):
        return os.path.join(storagePath, file_location)

    def cleanup_related_entities(self, id: int, local_db_session):
        local_db_session.query(ParentStageModel).filter(
            ParentStageModel.child_asset_id == id
        ).delete(synchronize_session=False)
        local_db_session.query(MediaTagModel).filter(MediaTagModel.asset_id == id).delete(
            synchronize_session=False
        )
        local_db_session.query(AssetLicenseModel).filter(AssetLicenseModel.asset_id == id).delete(
            synchronize_session=False
        )
        local_db_session.query(AssetUsageModel).filter(AssetUsageModel.asset_id == id).delete(
            synchronize_session=False
        )

    def remove_asset_from_frames(self, local_db_session, asset: AssetModel):
        for multiple_frame_media in (
            local_db_session.query(AssetModel)
            .filter(AssetModel.description.ilike(f"%{asset.file_location}%"))
            .all()
        ):
            attributes = json.loads(multiple_frame_media.description)
            for i, frame in enumerate(attributes["frames"]):
                if "?" in frame:
                    attributes["frames"][i] = frame[: frame.index("?")]
            if asset.file_location in attributes["frames"]:
                attributes["frames"].remove(asset.file_location)
            multiple_frame_media.description = json.dumps(attributes)
            local_db_session.flush()

    def assign_stages(self, input: AssignStagesInput):
        session = get_session()
        # Surviving assignments keep their parent_stage row, i.e. their
        # place in each stage's saved media order (see sync_asset_assignments).
        sync_asset_assignments(
            session, input.id, [(stage_id, None, None) for stage_id in input.stageIds]
        )
        session.flush()

        asset = session.query(AssetModel).filter_by(id=input.id).first()
        return self.asset_service.resolve_fields(asset)

    def update_stage_assignment(self, input: UpdateStageAssignmentInput, user: UserModel):
        session = get_session()
        row = (
            session.query(ParentStageModel)
            .filter(
                ParentStageModel.stage_id == input.stageId,
                ParentStageModel.child_asset_id == input.assetId,
            )
            .first()
        )
        if not row:
            raise GraphQLError("Media is not assigned to this stage")

        if (
            row.stage.owner_id != user.id
            and row.child_asset.owner_id != user.id
            and user.role not in [ADMIN, SUPER_ADMIN]
        ):
            raise GraphQLError("You are not authorized to update this stage")

        row.exit_animation = input.exitAnimation
        row.exit_speed = input.exitSpeed
        session.flush()
        return convert_keys_to_camel_case(row.to_dict())
