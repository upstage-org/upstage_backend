"""Every GraphQL mutation must release its row locks before the loop yields.

Companion to test_stage_last_access_lock.py, one layer up. Almost every
mutation flushes SQL inside its resolver, while request_session() commits at
request teardown, several event-loop yields later. Resolvers run ON the event
loop with blocking psycopg2, so a second request writing the same row in that
gap blocked the whole process behind a lock whose owner could never resume to
commit (2026-09-19 prod outage).

The shared fix is the ``end_transaction_after_root_mutation`` GraphQL
middleware. These tests drive a deliberately hazardous resolver (flush only,
no commit: the exact shape of the old updateLastAccess and of ~45 other write
sites) through Ariadne with that middleware, and never run the request
teardown, mirroring the moment another request gets the loop. File-backed
SQLite with one connection per session and a 1 s busy timeout makes a lock
that outlives the resolver fail loudly as "database is locked".
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest
from ariadne import MutationType, QueryType, graphql, make_executable_schema
from graphql import GraphQLError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from upstage_backend.global_config import db_context
from upstage_backend.global_config.schema import end_transaction_after_root_mutation
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.services import stage as _registers_related_models  # noqa: F401  (StageModel's mapper needs User/ParentStage/... imported)

TYPE_DEFS = """
    type Query { stageName(id: Int!): String }
    type Mutation {
        touch(id: Int!): String
        touchAsync(id: Int!): String
        touchThenRaise(id: Int!): String
        touchThenReturnError(id: Int!): String
    }
"""

query = QueryType()
mutation = MutationType()


def _flush_only_touch(id: int) -> str:
    session = db_context.get_session()
    stage = session.query(StageModel).filter(StageModel.id == id).first()
    stage.last_access = datetime.now()
    session.flush()  # row lock taken; no commit here, on purpose
    return stage.last_access.isoformat()


@query.field("stageName")
def resolve_stage_name(_, __, id):
    return db_context.get_session().get(StageModel, id).name


@mutation.field("touch")
def resolve_touch(_, __, id):
    return _flush_only_touch(id)


@mutation.field("touchAsync")
async def resolve_touch_async(_, __, id):
    await asyncio.sleep(0)
    return _flush_only_touch(id)


@mutation.field("touchThenRaise")
def resolve_touch_then_raise(_, __, id):
    _flush_only_touch(id)
    raise GraphQLError("boom")


@mutation.field("touchThenReturnError")
def resolve_touch_then_return_error(_, __, id):
    _flush_only_touch(id)
    return GraphQLError("returned, not raised")


SCHEMA = make_executable_schema(TYPE_DEFS, query, mutation)


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage.db'}",
        connect_args={"timeout": 1, "check_same_thread": False},
        future=True,
    )
    StageModel.__table__.create(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    with factory() as s:
        s.add(StageModel(id=1, name="Turn", file_location="turn", owner_id=1))
        s.commit()
    yield factory
    engine.dispose()


def _execute(session_factory, document, *, middleware=(end_transaction_after_root_mutation,)):
    """Run one GraphQL request with its own bound session and NO teardown
    commit. Returns (result, session); the caller closes the session."""
    session = session_factory()
    token = db_context.set_session(session)
    try:
        _, result = asyncio.run(graphql(SCHEMA, {"query": document}, middleware=list(middleware)))
        return result, session
    finally:
        db_context.reset_session(token)


def _last_access(session_factory):
    with session_factory() as s:
        return s.get(StageModel, 1).last_access


@pytest.mark.parametrize("field", ["touch", "touchAsync"])
def test_concurrent_mutations_on_same_row_do_not_block(session_factory, field):
    doc = f"mutation {{ {field}(id: 1) }}"
    result_a, session_a = _execute(session_factory, doc)
    assert "errors" not in result_a
    assert not session_a.in_transaction()
    # Request B gets the loop before A's teardown. This is where prod hung.
    result_b, session_b = _execute(session_factory, doc)
    assert "errors" not in result_b, result_b
    assert _last_access(session_factory).isoformat() == result_b["data"][field]
    session_a.close()
    session_b.close()


def test_without_the_middleware_the_second_writer_is_locked_out(session_factory):
    # Pins that the scenario above really reproduces the hazard, so the test
    # cannot rot into passing for the wrong reason.
    doc = "mutation { touch(id: 1) }"
    _, session_a = _execute(session_factory, doc, middleware=())
    assert session_a.in_transaction()
    result_b, session_b = _execute(session_factory, doc, middleware=())
    assert "database is locked" in str(result_b.get("errors"))
    session_a.close()
    session_b.close()


@pytest.mark.parametrize("field", ["touchThenRaise", "touchThenReturnError"])
def test_failed_mutation_rolls_back_and_releases_the_lock(session_factory, field):
    result, session = _execute(session_factory, f"mutation {{ {field}(id: 1) }}")
    assert result["errors"]
    assert not session.in_transaction()
    assert _last_access(session_factory) is None
    session.close()


def test_queries_pass_through_untouched(session_factory):
    result, session = _execute(session_factory, "{ stageName(id: 1) }")
    assert result["data"]["stageName"] == "Turn"
    assert session.in_transaction()  # read-only snapshot, closed at teardown
    session.close()


def test_the_real_graphql_app_is_built_with_the_middleware():
    from fastapi import FastAPI

    from upstage_backend.global_config.schema import config_graphql_endpoints

    app = FastAPI()
    config_graphql_endpoints(app)
    gql_app = next(
        r.endpoint for r in app.routes if getattr(r, "path", "") == "/api/studio_graphql"
    )
    assert end_transaction_after_root_mutation in gql_app.http_handler.middleware


def _run_concurrently(session_factory, document, n, middleware):
    """N requests as N tasks on ONE event loop, each with its own session
    bound in its own task context (tasks copy the ContextVar context), the
    way uvicorn runs them. No request ever runs its teardown commit, so any
    lock that outlives a resolver is still held when the next task runs."""
    sessions = []

    async def one_request():
        session = session_factory()
        sessions.append(session)
        db_context.set_session(session)
        _, result = await graphql(SCHEMA, {"query": document}, middleware=list(middleware))
        return result

    async def main():
        return await asyncio.gather(*(one_request() for _ in range(n)))

    try:
        return asyncio.run(main()), [s.in_transaction() for s in sessions]
    finally:
        for s in sessions:
            s.close()


def test_many_concurrent_requests_on_one_loop_all_succeed(session_factory):
    # touchAsync yields before writing, so the tasks genuinely interleave.
    results, open_transactions = _run_concurrently(
        session_factory,
        "mutation { touchAsync(id: 1) }",
        n=25,
        middleware=(end_transaction_after_root_mutation,),
    )
    assert [r for r in results if "errors" in r] == []
    assert not any(open_transactions)
    stamps = sorted(r["data"]["touchAsync"] for r in results)
    assert _last_access(session_factory).isoformat() == stamps[-1]


def test_concurrent_requests_without_the_middleware_lock_each_other_out(session_factory):
    results, open_transactions = _run_concurrently(
        session_factory, "mutation { touchAsync(id: 1) }", n=3, middleware=()
    )
    assert open_transactions[0]  # first writer still holds the lock
    assert sum("database is locked" in str(r.get("errors")) for r in results) == 2
