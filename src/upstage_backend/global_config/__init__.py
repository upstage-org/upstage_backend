# -*- coding: iso8859-15 -*-
import os
import sys

from upstage_backend.global_config.database import ScopedSession, DBSession
from upstage_backend.global_config.db_context import (
    get_session,
    set_session,
    reset_session,
    request_session,
    SessionFactory,
)
import upstage_backend.global_config.env
from upstage_backend.global_config.env import *
from upstage_backend.global_config.schema import config_graphql_endpoints
from upstage_backend.global_config.db_models.base import BaseModel
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.global_config.helpers import (
    encrypt,
    decrypt,
    snake_to_camel,
    convert_keys_to_camel_case,
    camel_to_snake,
)
from upstage_backend.global_config.logger import logger

__all__ = [
    "encrypt",
    "decrypt",
    "snake_to_camel",
    "convert_keys_to_camel_case",
    "db",
    "ScopedSession",
    "config_graphql_endpoints",
    "DBSession",
    "get_session",
    "set_session",
    "reset_session",
    "request_session",
    "SessionFactory",
    "camel_to_snake",
    "BaseModel",
    "authenticated",
    "logger",
]

__all__ += [name for name in dir(sys.modules["upstage_backend.global_config.env"]) if not name.startswith("__")]
