"""updateLastAccess must never hold a row lock across an event-loop yield.

Ariadne runs sync resolvers directly on the uvicorn event loop, and the DB
engine is sync psycopg2. On 2026-09-19 prod froze mid-performance: two
audience members loaded the same stage 20 ms apart. Request A flushed
``UPDATE stage SET last_access=...`` (taking the row lock) and returned to
the loop, leaving the COMMIT to the request middleware. Request B's resolver
then ran the same UPDATE synchronously and blocked the whole process inside
psycopg2 waiting for A's lock, so A could never resume to commit. Postgres
cannot see that deadlock (A is idle-in-transaction, not waiting on a lock).

Two guardrails are pinned here:

1. ``StageService.update_last_access`` commits before returning, so the row
   lock is gone by the time control goes back to the event loop. The
   two-writer test reproduces the outage shape with a file-backed SQLite
   database (one connection per session, 1 s busy timeout): with the old
   flush-only body the second writer dies with "database is locked".
2. ``global_config.database`` asks Postgres for ``lock_timeout`` and
   ``idle_in_transaction_session_timeout`` on every connection, so any
   future contended statement fails one request instead of freezing prod.
"""

from __future__ import annotations

import runpy
from datetime import datetime

import pytest
import sqlalchemy
from graphql import GraphQLError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from upstage_backend.global_config import db_context
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.services.stage import StageService


@pytest.fixture
def session_factory(tmp_path):
    # File-backed (not :memory:/StaticPool) so each Session gets its own
    # DBAPI connection and SQLite's writer lock behaves like a real row
    # lock between two concurrent requests. 1 s busy timeout keeps a
    # regression loud and fast rather than hanging the suite.
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage.db'}",
        connect_args={"timeout": 1, "check_same_thread": False},
        future=True,
    )
    StageModel.__table__.create(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    engine.dispose()


@pytest.fixture
def stage_id(session_factory):
    with session_factory() as s:
        stage = StageModel(name="Turn", file_location="turn", owner_id=1)
        s.add(stage)
        s.commit()
        return stage.id


def _as_request(session_factory, fn):
    """Run ``fn(session)`` with ``session`` bound as the request session,
    exactly as the db_request_session middleware does — but WITHOUT the
    middleware's teardown commit, mirroring the moment a resolver has
    returned and the event loop is free to run another request."""
    session = session_factory()
    token = db_context.set_session(session)
    try:
        return fn(session), session
    finally:
        db_context.reset_session(token)


def test_update_last_access_commits_before_returning(session_factory, stage_id):
    result, session = _as_request(
        session_factory, lambda s: StageService().update_last_access(stage_id)
    )
    assert isinstance(result["result"], datetime)
    # The invariant that prevents the deadlock: no open transaction (hence
    # no row lock) survives the resolver's return.
    assert not session.in_transaction()
    with session_factory() as fresh:
        assert fresh.get(StageModel, stage_id).last_access == result["result"]
    session.close()


def test_two_requests_touching_same_stage_do_not_block_each_other(session_factory, stage_id):
    # Request A returns from the resolver; its middleware commit has not run.
    result_a, session_a = _as_request(
        session_factory, lambda s: StageService().update_last_access(stage_id)
    )
    # Request B is scheduled on the loop before A's teardown and touches the
    # same row. With a lock still held by A this is where prod hung.
    result_b, session_b = _as_request(
        session_factory, lambda s: StageService().update_last_access(stage_id)
    )
    assert result_b["result"] >= result_a["result"]
    assert not session_a.in_transaction()
    assert not session_b.in_transaction()
    with session_factory() as fresh:
        assert fresh.get(StageModel, stage_id).last_access == result_b["result"]
    session_a.close()
    session_b.close()


def test_unknown_stage_raises_and_leaves_no_open_transaction(session_factory):
    def call(_):
        with pytest.raises(GraphQLError):
            StageService().update_last_access(999_999)

    _, session = _as_request(session_factory, call)
    assert not session.in_transaction()
    session.close()


def test_engine_requests_lock_and_idle_transaction_timeouts(monkeypatch):
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured.update(kwargs)
        return object()

    # Re-run the module body in a throwaway namespace so the real, already
    # imported engine is untouched.
    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)
    runpy.run_module("upstage_backend.global_config.database", run_name="_probe")

    options = captured["connect_args"]["options"]
    assert "-c lock_timeout=" in options
    assert "-c idle_in_transaction_session_timeout=" in options
    lock_ms = int(options.split("lock_timeout=")[1].split()[0])
    assert 0 < lock_ms <= 10_000, (
        "lock_timeout must be short enough to fail one request, not stall prod"
    )
