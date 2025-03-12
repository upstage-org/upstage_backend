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

from ariadne import QueryType, make_executable_schema

from performance_config.services.performance import PerformanceService
from performance_config.services.scene import SceneService
from stages.services.stage import StageService
from ariadne.asgi import GraphQL
from studio_management.http.graphql import type_defs


query = QueryType()


@query.field("performanceCommunication")
def performance_communication(*_):
    return PerformanceService().get_performance_communication()


@query.field("performanceConfig")
def performance_config(*_):
    return PerformanceService().get_performance_config()


@query.field("scene")
def scene(*_):
    return SceneService().get_scene()


@query.field("parentStage")
def parent_stage(*_):
    return StageService().get_parent_stage()


schema = make_executable_schema(type_defs, query)
performance_graphql_app = GraphQL(schema, debug=True)
