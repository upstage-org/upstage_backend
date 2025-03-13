# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir2 not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from global_config.database import ScopedSession, DBSession, global_session
import global_config.env
from global_config.env import *
from global_config.schema import config_graphql_endpoints
from global_config.db_models.base import BaseModel
from global_config.decorators.authenticated import authenticated
from global_config.helpers import (
    encrypt,
    decrypt,
    snake_to_camel,
    convert_keys_to_camel_case,
    camel_to_snake,
)

__all__ = [
    "encrypt",
    "decrypt",
    "snake_to_camel",
    "convert_keys_to_camel_case",
    "db",
    "ScopedSession",
    "config_graphql_endpoints",
    "DBSession",
    "global_session",
    "camel_to_snake",
    "BaseModel",
    "authenticated",
]

__all__ += [name for name in dir(global_config.env) if not name.startswith('__')]

