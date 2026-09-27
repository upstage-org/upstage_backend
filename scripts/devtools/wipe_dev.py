import os
import sys

import pathlib

from sqlalchemy import delete, not_, select
from terminal_colors import bcolors
from upstage_backend.global_config import (
    UPLOAD_USER_CONTENT_FOLDER,
    ScopedSession,
    logger,
)
from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
from upstage_backend.assets.db_models.asset_usage import AssetUsageModel
from upstage_backend.assets.db_models.media_tag import MediaTagModel
from upstage_backend.event_archive.db_models.event import EventModel
from upstage_backend.performance_config.db_models.performance import PerformanceModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
from upstage_backend.performance_config.db_models.scene import SceneModel

stages_to_be_kepts = ["8thMarch"]

logger.warning(
    bcolors.WARNING
    + "Are you sure you want to do the clean up? This will delete all stages except {0}!".format(
        stages_to_be_kepts
    )
    + bcolors.ENDC
)
logger.info(
    'If you want to keep any stages, please add them to the "stages_to_be_kepts" list in "scripts/wipe_dev.py".'
)

if input(bcolors.BOLD + 'Type "confirm" to continue: ' + bcolors.ENDC) != "confirm":
    logger.error(bcolors.FAIL + "Aborted!" + bcolors.ENDC)
    sys.exit(0)

logger.info(bcolors.OKGREEN + "Start cleaning up..." + bcolors.ENDC)


with ScopedSession() as session:
    keep_ids = []
    for stage in session.scalars(select(StageModel)).all():
        if stage.file_location in stages_to_be_kepts:
            keep_ids.append(stage.id)

    session.execute(
        delete(ParentStageModel).where(ParentStageModel.stage_id.notin_(keep_ids)),
        execution_options={"synchronize_session": False},
    )

    for asset in session.scalars(select(AssetModel).where(not_(AssetModel.stages.any()))).all():
        logger.info("🗑️ Deleting asset: {}".format(asset.name))
        session.execute(
            delete(AssetLicenseModel).where(AssetLicenseModel.asset_id == asset.id),
            execution_options={"synchronize_session": False},
        )
        session.execute(
            delete(AssetUsageModel).where(AssetUsageModel.asset_id == asset.id),
            execution_options={"synchronize_session": False},
        )
        session.execute(
            delete(MediaTagModel).where(MediaTagModel.asset_id == asset.id),
            execution_options={"synchronize_session": False},
        )
        session.delete(asset)

    upload_assets_folder = "{}".format(UPLOAD_USER_CONTENT_FOLDER)

    for ftype in os.listdir(upload_assets_folder):
        if ("." not in ftype) and (".." not in ftype) and os.path.isdir(ftype):
            for media in os.listdir("{}/{}".format(upload_assets_folder, ftype)):
                if not session.scalars(
                    select(AssetModel)
                    .where(AssetModel.file_location == "{}/{}".format(ftype, media))
                    .limit(1)
                ).first():
                    logger.info("🗑️ Deleting file {}/{}".format(ftype, media))
                    try:
                        pathlib.Path("{}/{}/{}".format(upload_assets_folder, ftype, media)).unlink()
                    except Exception:
                        logger.error(
                            "Failed to remove {}/{}/{}".format(upload_assets_folder, ftype, media)
                        )

    for stage in session.scalars(select(StageModel)).all():
        if stage.file_location not in stages_to_be_kepts:
            logger.info("🗑️ Deleting stage: {}".format(stage.name))
            session.execute(
                delete(StageAttributeModel).where(StageAttributeModel.stage_id == stage.id),
                execution_options={"synchronize_session": False},
            )
            sample_event = session.scalars(
                select(EventModel)
                .where(
                    EventModel.performance_id.in_(
                        select(PerformanceModel.id).where(PerformanceModel.stage_id == stage.id)
                    )
                )
                .limit(1)
            ).first()
            if sample_event:
                session.execute(
                    delete(EventModel).where(EventModel.topic == sample_event.topic),
                    execution_options={"synchronize_session": False},
                )
            session.execute(
                delete(PerformanceModel).where(PerformanceModel.stage_id == stage.id),
                execution_options={"synchronize_session": False},
            )
            session.execute(
                delete(SceneModel).where(SceneModel.stage_id == stage.id),
                execution_options={"synchronize_session": False},
            )
            session.delete(stage)
        else:
            logger.info("🗑️ Clearing replays and scenes of {}".format(stage.name))
            session.execute(
                delete(PerformanceModel).where(PerformanceModel.stage_id == stage.id),
                execution_options={"synchronize_session": False},
            )
            session.execute(
                delete(SceneModel).where(SceneModel.stage_id == stage.id),
                execution_options={"synchronize_session": False},
            )

    session.commit()
    session.close()

logger.info("Done!")
