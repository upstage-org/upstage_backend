from ariadne import QueryType

from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.performance_config.services.performance import PerformanceService
from upstage_backend.performance_config.services.scene import SceneService
from upstage_backend.stages.services.stage import StageService
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN


query = QueryType()


# Whole-table dumps (the MQTT config one includes broker passwords). None of
# these is used by the studio UI; they were unauthenticated.
@query.field("performanceCommunication")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def performance_communication(*_):
    return PerformanceService().get_performance_communication()


@query.field("performanceConfig")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def performance_config(*_):
    return PerformanceService().get_performance_config()


@query.field("scene")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def scene(*_):
    return SceneService().get_scene()


@query.field("parentStage")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def parent_stage(*_):
    return StageService().get_parent_stage()
