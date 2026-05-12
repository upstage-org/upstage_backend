# -*- coding: iso8859-15 -*-

from upstage_backend.global_config.logger import logger

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from upstage_backend.global_config.env import DATABASE_URL

# `engine` here is lazy: SQLAlchemy doesn't open a socket until the first
# `engine.connect()` / `Session` checkout. The previous module body also
# carried an unused `database = Database(DATABASE_URL)` (databases lib) and
# `metadata = MetaData(); metadata.create_all(engine)` pair. The MetaData
# was empty (every model registers itself against `BaseModel.metadata`,
# never this one), so create_all was a no-op apart from forcing an eager
# Postgres connection at import time. That eager connection broke
# `pytest --collect-only` from the host (whenever `postgres_container_dev`
# isn't resolvable) and offered no production value — table creation runs
# through Alembic. Both were removed.
engine = create_engine(DATABASE_URL, poolclass=NullPool, query_cache_size=0)


class ScopedSession(object):
    """
    Use this for local session scope OUTSIDE an HTTP request (scripts,
    background workers, migrations, ad-hoc jobs).

    Inside FastAPI/GraphQL request handlers, call
    `global_config.get_session()` instead - it returns the request's
    own Session, opened by the request_session middleware.

    Usage:
        with ScopedSession() as local_db_session:
           local_db_session.add(some_obj)
           local_db_session.flush()  # if you need the ID right away
           rows = local_db_session.query(Model).filter(...).all()

    Session will be committed and closed when you fall out of scope.
    Rollback on exception is default; pass rollback_upon_failure=False
    to disable.
    """

    def __init__(self, rollback_upon_failure=True):
        from upstage_backend.global_config.db_context import SessionFactory

        self._factory = SessionFactory
        self.session = None
        self.rollback_upon_failure = rollback_upon_failure

    def __enter__(self):
        self.session = self._factory()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session is None:
            return False
        try:
            if exc_type is not None:
                if self.rollback_upon_failure:
                    try:
                        self.session.rollback()
                    except Exception:
                        logger.exception(
                            "ScopedSession: rollback after handler error failed"
                        )
                else:
                    logger.error(
                        "ScopedSession: handler raised but rollback_upon_failure=False"
                    )
            else:
                try:
                    self.session.commit()
                except Exception as e:
                    if self.rollback_upon_failure:
                        try:
                            self.session.rollback()
                        except Exception:
                            logger.exception(
                                "ScopedSession: commit failed and rollback also failed"
                            )
                        logger.error(
                            f"ScopedSession: failed to commit, rolled back: {e}"
                        )
                    else:
                        logger.error(
                            f"ScopedSession: failed to commit, NOT rolled back per request: {e}"
                        )
        finally:
            try:
                self.session.close()
            except Exception:
                logger.exception("ScopedSession: session.close() failed")
            self.session = None
        return False


class _RequestSessionProxy:
    """
    Deprecated thin proxy for the legacy module-level `DBSession`. Every
    attribute access is forwarded to the Session that's bound on the
    request contextvar via `get_session()`. This lets in-flight call
    sites like `DBSession.query(Model).filter(...)` keep working during
    the scoped-session refactor.

    Prefer `session = get_session()` directly in new and migrated code.
    This alias will be removed once all call sites are migrated.
    """

    __slots__ = ()

    def _target(self):
        from upstage_backend.global_config.db_context import get_session

        return get_session()

    def __getattr__(self, name):
        return getattr(self._target(), name)

    def __call__(self, *args, **kwargs):
        return self._target()(*args, **kwargs)

    def __repr__(self):
        return "<DBSession deprecated alias -> request contextvar Session>"


DBSession = _RequestSessionProxy()
