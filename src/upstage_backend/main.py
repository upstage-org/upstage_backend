# -*- coding: iso8859-15 -*-
import os
import sys

from fastapi import FastAPI
from fastapi_exception import FastApiException
from fastapi_global_variable import GlobalVariable
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.requests import Request

from upstage_backend.global_config import ENV_TYPE, config_graphql_endpoints, HOSTNAME
from upstage_backend.global_config.db_context import request_session, current_session_or_none
from upstage_backend.global_config.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def add_cors_middleware(app):
    allowed_origins = ["*"] if ENV_TYPE != "Production" else [HOSTNAME, f"*.{HOSTNAME}"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class Bootstrap:
    def __init__(self, app: FastAPI):
        self.app = app

    def init_exception(self):
        FastApiException.config()


def start_app():
    bootstrap = Bootstrap(app)
    add_cors_middleware(app)
    config_graphql_endpoints(app)
    bootstrap.init_exception()


app = FastAPI(title="upstage", lifespan=lifespan)
GlobalVariable.set("app", app)


@app.middleware("http")
async def no_store_api_responses(request: Request, call_next):
    """Prevent CDN/browser caching of dynamic API responses (e.g. Cloudflare POST cache rules)."""
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


@app.middleware("http")
async def db_request_session(request: Request, call_next):
    """
    Bind one SQLAlchemy Session to the contextvar for the life of this
    HTTP request. request_session() commits on clean exit, rolls back
    on exceptions, and always closes.

    Note: FastAPI runs @app.middleware("http") handlers in reverse
    registration order, so this handler (registered second) wraps
    closest to the route, which is exactly what we want: the session
    is open while the route/resolvers run and closes before
    no_store_api_responses attaches headers.
    """
    with request_session() as session:
        try:
            response = await call_next(request)
        except Exception:
            raise
        else:
            if (
                current_session_or_none() is session
                and (session.new or session.dirty or session.deleted)
            ):
                logger.warning(
                    "db_request_session: request %s finished with uncommitted "
                    "pending changes; request_session() will commit them now.",
                    request.url.path,
                )
        return response


start_app()
