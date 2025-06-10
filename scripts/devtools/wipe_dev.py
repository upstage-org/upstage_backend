import os
import sys

import pathlib

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)

from sqlalchemy import not_
from terminal_colors import bcolors
from src.global_config import UPLOAD_USER_CONTENT_FOLDER, ScopedSession, logger
from src.assets.db_models.asset import AssetModel
from src.assets.db_models.asset_license import AssetLicenseModel
from src.assets.db_models.asset_usage import AssetUsageModel
from src.assets.db_models.media_tag import MediaTagModel
from src.event_archive.db_models.event import EventModel
from src.performance_config.db_models.performance import PerformanceModel
from src.stages.db_models.stage import StageModel
from src.stages.db_models.parent_stage import ParentStageModel
from src.stages.db_models.stage_attribute import StageAttributeModel
from src.performance_config.db_models.scene import SceneModel

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
    for stage in session.query(StageModel).all():
        if stage.file_location in stages_to_be_kepts:
            keep_ids.append(stage.id)

    session.query(ParentStageModel).filter(ParentStageModel.stage_id.notin_(keep_ids)).delete(
        synchronize_session=False
    )

    for asset in session.query(AssetModel).filter(not_(AssetModel.stages.any())).all():
        logger.info("🗑️ Deleting asset: {}".format(asset.name))
        session.query(AssetLicenseModel).filter(AssetLicenseModel.asset_id == asset.id).delete(
            synchronize_session=False
        )
        session.query(AssetUsageModel).filter(AssetUsageModel.asset_id == asset.id).delete(
            synchronize_session=False
        )
        session.query(MediaTagModel).filter(MediaTagModel.asset_id == asset.id).delete(
            synchronize_session=False
        )
        session.delete(asset)

    upload_assets_folder = "{}".format(UPLOAD_USER_CONTENT_FOLDER)

    for ftype in os.listdir(upload_assets_folder):
        if ("." not in ftype) and (".." not in ftype) and os.path.isdir(ftype):
            for media in os.listdir("{}/{}".format(upload_assets_folder, ftype)):
                if (
                    not session.query(AssetModel)
                    .filter(AssetModel.file_location == "{}/{}".format(ftype, media))
                    .first()
                ):
                    logger.info("🗑️ Deleting file {}/{}".format(ftype, media))
                    try:
                        pathlib.Path(
                            "{}/{}/{}".format(upload_assets_folder, ftype, media)
                        ).unlink()
                    except:
                        logger.error(
                            "Failed to remove {}/{}/{}".format(
                                upload_assets_folder, ftype, media
                            )
                        )

    for stage in session.query(StageModel).all():
        if stage.file_location not in stages_to_be_kepts:
            logger.info("🗑️ Deleting stage: {}".format(stage.name))
            session.query(StageAttributeModel).filter(
                StageAttributeModel.stage_id == stage.id
            ).delete(synchronize_session=False)
            sample_event = (
                session.query(EventModel)
                .filter(
                    EventModel.performance_id.in_(
                        session.query(PerformanceModel.id).filter(
                            PerformanceModel.stage_id == stage.id
                        )
                    )
                )
                .first()
            )
            if sample_event:
                session.query(EventModel).filter(EventModel.topic == sample_event.topic).delete(
                    synchronize_session=False
                )
            session.query(PerformanceModel).filter(PerformanceModel.stage_id == stage.id).delete(
                synchronize_session=False
            )
            session.query(SceneModel).filter(SceneModel.stage_id == stage.id).delete(
                synchronize_session=False
            )
            session.delete(stage)
        else:
            logger.info("🗑️ Clearing replays and scenes of {}".format(stage.name))
            session.query(PerformanceModel).filter(PerformanceModel.stage_id == stage.id).delete(
                synchronize_session=False
            )
            session.query(SceneModel).filter(SceneModel.stage_id == stage.id).delete(
                synchronize_session=False
            )

    session.commit()
    session.close()

logger.info("Done!")
