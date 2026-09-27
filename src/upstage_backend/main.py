import loguru  # noqa: F401  # entrypoint: load loguru before upstage (see app_containers compose)

from fastapi import FastAPI
from fastapi_exception import FastApiException
from fastapi_global_variable import GlobalVariable
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import ClientDisconnect, Request
from starlette.responses import Response

import re

from upstage_backend.assets.http.rtmp_auth import router as rtmp_auth_router
from upstage_backend.global_config import ENV_TYPE, config_graphql_endpoints
from upstage_backend.global_config.env import DOMAIN, UPSTAGE_FRONTEND_URL
from upstage_backend.global_config.db_context import (
    request_session,
    current_session_or_none,
)
from upstage_backend.global_config.logger import logger


def add_cors_middleware(app):
    """
    The SPA is served same-origin behind nginx (`/api` is proxied), so CORS
    only matters for other origins. Starlette compares full origins
    (scheme + host) and has no glob support, so the old Production list
    `[HOSTNAME, "*.HOSTNAME"]` (with HOSTNAME being the dot-mangled
    socket.gethostname()) never matched anything. Production now allows the
    configured frontend URL plus https sub-domains of DOMAIN.
    """
    if ENV_TYPE != "Production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[UPSTAGE_FRONTEND_URL.rstrip("/")],
        allow_origin_regex=rf"^https://([a-z0-9-]+\.)*{re.escape(DOMAIN)}$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class Bootstrap:
    def __init__(self, app: FastAPI):
        self.app = app

    def init_exception(self):
        FastApiException.config()
        # A browser aborting an in-flight request (page navigation, flaky
        # network) raises ClientDisconnect while the body is being read.
        # Without a class-specific handler it falls through to the catch-all
        # Exception handler in ServerErrorMiddleware, which re-raises and
        # makes uvicorn log a full "Exception in ASGI application" traceback
        # for what is routine client behavior. Answer 499 (nginx's "client
        # closed request") — nobody is listening anyway.
        self.app.add_exception_handler(ClientDisconnect, _client_disconnect_handler)


async def _client_disconnect_handler(request: Request, exc: ClientDisconnect) -> Response:
    return Response(status_code=499)


def start_app():
    bootstrap = Bootstrap(app)
    add_cors_middleware(app)
    config_graphql_endpoints(app)
    app.include_router(rtmp_auth_router)
    bootstrap.init_exception()


app = FastAPI(title="upstage")
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
            if current_session_or_none() is session and (
                session.new or session.dirty or session.deleted
            ):
                logger.warning(
                    "db_request_session: request %s finished with uncommitted "
                    "pending changes; request_session() will commit them now.",
                    request.url.path,
                )
        return response


start_app()
