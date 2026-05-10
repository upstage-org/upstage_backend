# -*- coding: iso8859-15 -*-
"""
Root pytest conftest.

Keep this file's top-level imports stdlib-only. Anything that pulls in
``upstage_backend.global_config`` (or transitively ``upstage_backend.main``)
forces ``global_config.database.create_engine(DATABASE_URL)`` and
``metadata.create_all(engine)`` to run at import time, which fails immediately
on hosts where ``postgres_container_dev`` is not resolvable (anywhere outside
the docker-compose network). That broke ``pytest --collect-only`` from the
host, which in turn made it impossible to lint or count tests without bringing
the whole stack up.

The actual ``app``/``DATABASE_URL`` imports are pushed into the fixtures that
need them so collection only requires the upstage_backend package to be
importable, not its database to be reachable.
"""

import time

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def client():
    from starlette.testclient import TestClient

    from upstage_backend.global_config import logger
    from upstage_backend.main import app

    with TestClient(app=app, base_url="http://localhost:8000") as test_client:
        logger.info("Client is ready")
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def db_engine():
    from sqlalchemy import create_engine, text

    from upstage_backend.global_config import env, logger

    engine = create_engine(env.DATABASE_URL)
    yield engine
    start_time = time.time()
    engine.dispose()
    with create_engine(
        env.DATABASE_URL.rsplit("/", 1)[0], isolation_level="AUTOCOMMIT"
    ).connect() as connection:
        connection.execute(
            text(
                f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{env.DATABASE_NAME}'
            AND pid <> pg_backend_pid();
        """
            )
        )
        # connection.execute(text(f"DROP DATABASE {env.DATABASE_NAME}"))
    end_time = time.time()
    logger.info(f"Time taken to drop all tables: {end_time - start_time} seconds")
