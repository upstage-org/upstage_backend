from ariadne import MutationType, ObjectType, QueryType
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.global_config.env import MQTT_PASSWORD, MQTT_USER
from upstage_backend.performance_config.services.performance import PerformanceService
from upstage_backend.performance_config.services.scene import SceneService

from upstage_backend.stages.http.validation import (
    AssignMediaInput,
    AssignStagesInput,
    DuplicatePerformanceTrimInput,
    DuplicateStageInput,
    PerformanceInput,
    RecordInput,
    SceneInput,
    SearchStageInput,
    UpdateStageInput,
    StageInput,
    StageStreamInput,
    UpdateMediaInput,
    UpdateStageAssignmentInput,
    UploadMediaInput,
)
from upstage_backend.stages.services.media import MediaService
from upstage_backend.stages.services.stage import StageService
from upstage_backend.users.db_models.user import ADMIN, PLAYER, SUPER_ADMIN
from upstage_backend.global_config.helpers.context import current_user

query = QueryType()
mutation = MutationType()
stage_type = ObjectType("Stage")


@stage_type.field("mqtt")
def resolve_stage_mqtt(stage, info):
    """Broker login for the browser's own mqtt.js client.

    A field resolver rather than a key on the dicts built in StageService so it
    is evaluated ONLY when a query selects it: `foyerStageList` and the admin
    list views return [Stage] too, and none of them should carry a credential.

    Shared account for now, so `stage` is unused — it is the hook a per-session
    / stage-scoped credential would mint against later, without a schema change
    or a frontend redeploy.
    """
    return {"username": MQTT_USER, "password": MQTT_PASSWORD}


@query.field("stages")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def search_stages(_, info, input):
    return StageService().get_all_stages(
        current_user(info),
        SearchStageInput(**input),
    )


@query.field("stageList")
def stage_list(_, info, input: StageStreamInput):
    return StageService().get_stage_list(info, StageStreamInput(**input))


@query.field("foyerStageList")
def foyer_stage_list(_, info):
    return StageService().get_foyer_stage_list()


@query.field("stage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def get_stage(_, info, id: int):
    return StageService().get_stage_by_id(
        current_user(info), id
    )


@query.field("notifications")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def get_notifications(_, info):
    return StageService().get_notifications(current_user(info))


@mutation.field("createStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def create_stage(_, info, input):
    return StageService().create_stage(
        current_user(info), StageInput(**input)
    )


@mutation.field("updateStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def update_stage(_, info, input):
    return StageService().update_stage(
        current_user(info),
        UpdateStageInput(**input),
    )


@mutation.field("deleteStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def delete_stage(_, info, id):
    return StageService().delete_stage(current_user(info), id)


@mutation.field("duplicateStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def duplicate_stage(_, info, id: int, name: str):
    return StageService().duplicate_stage(
        current_user(info),
        DuplicateStageInput(id=id, name=name),
    )


@mutation.field("assignMedia")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def assign_media(_, info, input: AssignMediaInput):
    return MediaService().assign_media(
        AssignMediaInput(**input),
        current_user(info),
    )


@mutation.field("uploadMedia")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def upload_media(_, info, input: UploadMediaInput):
    return await MediaService().upload_media(
        current_user(info),
        UploadMediaInput(**input),
    )


@mutation.field("updateMedia")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def update_media(_, info, input: UpdateMediaInput):
    return await MediaService().update_media(
        UpdateMediaInput(**input),
        current_user(info),
    )


@mutation.field("deleteMediaOnStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def delete_media(_, info, id: int):
    return MediaService().delete_media(
        id, current_user(info)
    )


@mutation.field("assignStages")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def assign_stages(_, info, input: AssignStagesInput):
    return MediaService().assign_stages(
        AssignStagesInput(**input), current_user(info)
    )


@mutation.field("updateStageAssignment")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def update_stage_assignment(_, info, stageId, assetId, exitAnimation=None, exitSpeed=None):
    return MediaService().update_stage_assignment(
        UpdateStageAssignmentInput(
            stageId=stageId,
            assetId=assetId,
            exitAnimation=exitAnimation,
            exitSpeed=exitSpeed,
        ),
        current_user(info),
    )


@mutation.field("sweepStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def sweep_stage(_, info, id: int):
    return StageService().sweep_stage(current_user(info), id)


@mutation.field("saveScene")
@authenticated()
def save_scene(_, info, input: SceneInput):
    return SceneService().create_scene(
        current_user(info), SceneInput(**input)
    )


@mutation.field("deleteScene")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def delete_scene(_, info, id: int):
    return SceneService().delete_scene(current_user(info), id)


@mutation.field("updatePerformance")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def update_performance(_, info, input):
    return PerformanceService().update_performance(
        current_user(info),
        PerformanceInput(**input),
    )


@mutation.field("deletePerformance")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def delete_performance(_, info, id: int):
    return PerformanceService().delete_performance(
        current_user(info), id
    )


@mutation.field("duplicatePerformanceWithTrimmedPauses")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def duplicate_performance_with_trimmed_pauses(_, info, input):
    return PerformanceService().duplicate_performance_with_trimmed_pauses(
        current_user(info),
        DuplicatePerformanceTrimInput(**input),
    )


@mutation.field("startRecording")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def start_recording(_, info, input):
    return PerformanceService().create_performance(
        current_user(info),
        RecordInput(**input),
    )


@mutation.field("saveRecording")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def save_recording(_, info, id: int):
    return PerformanceService().save_recording(
        current_user(info), id
    )


@mutation.field("updateStatus")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def update_status(_, info, id: int):
    return StageService().update_status(current_user(info), id)


@mutation.field("updateVisibility")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def update_visibility(_, info, id: int):
    return StageService().update_visibility(
        current_user(info), id
    )


@mutation.field("updateLastAccess")
def update_last_access(_, __, id: int):
    return StageService().update_last_access(id)
