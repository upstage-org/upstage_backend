from upstage_backend.global_config.logger import logger

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool, QueuePool

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
# Per-connection Postgres safety net. Sync resolvers run on the uvicorn
# event loop (Ariadne does not thread-pool them) with blocking psycopg2, so
# a statement that waits on a row lock stalls the whole process. With
# lock_timeout, a contended statement fails that one request after 5 s
# instead of freezing prod; idle_in_transaction_session_timeout reaps any
# transaction a yielded request leaves open (see 2026-09-19 outage).
#
# Pooling: a small QueuePool instead of NullPool. NullPool opened a fresh
# Postgres connection (TLS + auth + the `options` round-trip) for every
# request, every email and every stats message. `pool_pre_ping` swaps a
# connection the server dropped (idle timeout, restart) for a fresh one
# instead of failing the request; `pool_recycle` retires connections before
# typical server-side idle limits. Returned connections are rolled back by
# SQLAlchemy, so the timeouts above still see a clean transaction.
#
# History: a first attempt (2026-09-27) timed out in the integration suite —
# not an app leak but the tests' own `get_session()` calls hitting
# db_context's non-strict fallback (a Session per test, never closed; see
# conftest.py `_test_body_session`) plus the GraphQL WebSocket fallback
# session (route removed). With both gone the suite holds ≤2 connections.
_PG_CONNECT_ARGS = {
    "options": "-c lock_timeout=5000 -c idle_in_transaction_session_timeout=120000"
}
_is_postgres = DATABASE_URL.startswith("postgresql")
engine = create_engine(
    DATABASE_URL,
    **(
        dict(
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=10,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args=_PG_CONNECT_ARGS,
        )
        if _is_postgres
        else dict(poolclass=NullPool)
    ),
)


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
                        logger.exception("ScopedSession: rollback after handler error failed")
                else:
                    logger.error("ScopedSession: handler raised but rollback_upon_failure=False")
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
                        logger.error(f"ScopedSession: failed to commit, rolled back: {e}")
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
