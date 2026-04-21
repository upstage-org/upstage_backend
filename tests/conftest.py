# -*- coding: iso8859-15 -*-
"""
Shared pytest configuration for upstage_backend tests.

This module MUST be imported before any `src.*` module so that env vars are
set and `global_config.database.engine` points at an in-memory SQLite engine
rather than trying to connect to a real Postgres at import time.
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("REFRESH_SECRET_KEY", "test-refresh-secret")
os.environ.setdefault("HOSTNAME", "localhost")
os.environ.setdefault("ENV_TYPE", "Test")
os.environ.setdefault("MQTT_BROKER", "localhost")
os.environ.setdefault("MQTT_ADMIN_USER", "test")
os.environ.setdefault("MQTT_ADMIN_PASSWORD", "test")
os.environ.setdefault("MQTT_ADMIN_PORT", "1883")
os.environ.setdefault("MQTT_TRANSPORT", "tcp")
os.environ.setdefault("PERFORMANCE_TOPIC_RULE", "+/+/+")
os.environ.setdefault("STRICT_DB_CONTEXT", "0")

import types as _types  # noqa: E402

if "databases" not in sys.modules:
    _stub = _types.ModuleType("databases")

    class _DatabaseStub:
        def __init__(self, *args, **kwargs):
            pass

        async def connect(self):
            return None

        async def disconnect(self):
            return None

    _stub.Database = _DatabaseStub
    sys.modules["databases"] = _stub

import pytest  # noqa: E402
from sqlalchemy import JSON as GenericJSON, create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture(scope="session")
def sqlite_engine():
    """
    One in-memory SQLite engine, shared across the whole test session by
    StaticPool so that every Session sees the same database.
    """
    from upstage_backend.event_archive.db_models.event import EventModel
    from upstage_backend.stages.db_models.stage import StageModel
    from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
    from upstage_backend.stages.db_models.parent_stage import ParentStageModel
    from upstage_backend.performance_config.db_models.performance import PerformanceModel
    from upstage_backend.performance_config.db_models.scene import SceneModel

    EventModel.__table__.c.payload.type = GenericJSON()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    for model in (
        EventModel,
        StageModel,
        StageAttributeModel,
        ParentStageModel,
        PerformanceModel,
        SceneModel,
    ):
        model.__table__.create(bind=engine, checkfirst=True)

    return engine


@pytest.fixture()
def rebound_db(sqlite_engine, monkeypatch):
    """
    Re-point every production code path at our SQLite engine for one test.

    Binds:
      * global_config.database.engine
      * global_config.db_context.SessionFactory  (used by request_session()
        and ScopedSession())
      * global_config.database.DBSession         (deprecated proxy alias,
        still expected by some legacy tests)

    Also opens a Session, binds it into the request ContextVar, and yields
    it as ``db_session`` equivalent. Tests can either access it via
    ``rebound_db['db_session']`` or simply call ``get_session()``.
    """
    import upstage_backend.global_config.database as db_module
    import upstage_backend.global_config.db_context as ctx_module

    monkeypatch.setattr(db_module, "engine", sqlite_engine, raising=True)

    test_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=sqlite_engine,
        expire_on_commit=False,
        future=True,
    )
    monkeypatch.setattr(
        ctx_module, "SessionFactory", test_session_factory, raising=True
    )

    session = test_session_factory()
    token = ctx_module.set_session(session)

    yield {
        "engine": sqlite_engine,
        "session_factory": test_session_factory,
        "db_session": session,
        "DBSession": session,
    }

    try:
        session.rollback()
    except Exception:
        pass
    try:
        session.close()
    except Exception:
        pass
    ctx_module.reset_session(token)

    with sqlite_engine.begin() as conn:
        from upstage_backend.event_archive.db_models.event import EventModel
        from upstage_backend.stages.db_models.stage import StageModel
        from upstage_backend.performance_config.db_models.performance import PerformanceModel

        for tbl in (
            EventModel.__table__,
            PerformanceModel.__table__,
            StageModel.__table__,
        ):
            conn.execute(tbl.delete())


@pytest.fixture()
def db_session(rebound_db):
    """
    Convenience fixture that yields the request-scoped Session pushed by
    ``rebound_db``. Prefer this in new tests so they read exactly what
    production code sees via ``get_session()``.
    """
    return rebound_db["db_session"]
