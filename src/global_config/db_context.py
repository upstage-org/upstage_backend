# -*- coding: iso8859-15 -*-
"""
Request-scoped SQLAlchemy session, stored in a ContextVar.

One Session per HTTP/GraphQL request. The FastAPI middleware in main.py
opens a session at the start of each request via request_session(),
stores it on a ContextVar, and commits/rolls-back/closes on request
teardown. Every service, resolver and test then reads the session with
get_session() instead of touching a module-level scoped_session.

Tests that have no HTTP request can use set_session() / reset_session()
manually; scripts and background workers that have no request at all
should continue to use ScopedSession from database.py for explicit scope.
"""
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional

from sqlalchemy.orm import Session, sessionmaker

from global_config.database import engine
from global_config.logger import logger


SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


_session_cv: ContextVar[Optional[Session]] = ContextVar(
    "upstage_request_session", default=None
)


def _strict_mode() -> bool:
    """
    When STRICT_DB_CONTEXT=1 (default in dev), get_session() raises if
    no session is bound. In production we keep the same behavior so
    that stray out-of-scope DB access is loud, not silent.
    """
    return os.getenv("STRICT_DB_CONTEXT", "1") != "0"


def get_session() -> Session:
    """
    Return the Session bound to the current HTTP/GraphQL request.

    Raises RuntimeError if nothing is bound on the contextvar. Callers
    that are NOT inside a request (scripts, workers, ad-hoc jobs)
    should use `with ScopedSession() as session:` instead.
    """
    session = _session_cv.get()
    if session is None:
        if _strict_mode():
            raise RuntimeError(
                "No request-scoped Session is bound. Call get_session() "
                "only from inside a FastAPI/GraphQL request, a test that "
                "set_session(), or a code path wrapped in request_session(). "
                "Scripts and background workers must use ScopedSession."
            )
        session = SessionFactory()
        _session_cv.set(session)
    return session


def set_session(session: Session) -> Token:
    """Bind `session` to the current context. Returns a token for reset."""
    return _session_cv.set(session)


def reset_session(token: Token) -> None:
    """Reset the contextvar to its previous value. Pairs with set_session()."""
    _session_cv.reset(token)


def current_session_or_none() -> Optional[Session]:
    """Non-raising probe used by dev-mode assertions and structured logs."""
    return _session_cv.get()


@contextmanager
def request_session() -> Iterator[Session]:
    """
    Context manager that owns a Session for the duration of one HTTP or
    GraphQL request. Commits on clean exit, rolls back on exception,
    always closes and unbinds from the contextvar.
    """
    session: Session = SessionFactory()
    token = _session_cv.set(session)
    try:
        yield session
        try:
            if session.in_transaction() or session.new or session.dirty or session.deleted:
                session.commit()
        except Exception:
            logger.exception("request_session: commit failed, rolling back")
            session.rollback()
            raise
    except Exception:
        try:
            session.rollback()
        except Exception:
            logger.exception("request_session: rollback after handler error also failed")
        raise
    finally:
        try:
            session.close()
        except Exception:
            logger.exception("request_session: session.close() failed")
        _session_cv.reset(token)
