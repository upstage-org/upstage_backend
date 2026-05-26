"""DB-free unit-test scope.

The repository-root `/conftest.py` declares `client` and `db_engine` as
`autouse=True` session fixtures that reach for a live Postgres via
`upstage_backend.global_config.env.DATABASE_URL`. That makes the rest
of the suite useful but unrunnable on a developer's machine without
docker, which is exactly the gap the pre-push gate has to fill.

This conftest sits inside `tests/unit/` and overrides those two
autouse fixtures with no-ops, so anything collected under
`tests/unit/` runs in pure Python with no database, no MQTT broker
and no FastAPI lifespan. Tests that genuinely need a DB belong in
`src/upstage_backend/<module>/tests/` (which use the in-memory
SQLite rebind from `tests/conftest.py::rebound_db`) or in
`tests/event_archive_tests/` — NOT here.

We also call `os.environ.setdefault` for the same env vars
`tests/conftest.py` sets, so plain `pytest tests/unit/` works
even when invoked WITHOUT `tests/conftest.py` on the search path
(pytest only descends through one conftest tree at a time).
"""

from __future__ import annotations

import os

# Match `tests/conftest.py` so module imports of `upstage_backend.*`
# do not blow up reaching for the real DATABASE_URL / SECRET_KEY.
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

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def client():
    """No-op override of root conftest's FastAPI TestClient fixture.

    The root fixture imports `upstage_backend.main:app`, which triggers
    DB engine creation. Tests under `tests/unit/` must not depend on
    that — they run before the docker stack is up.
    """
    yield None


@pytest.fixture(scope="session", autouse=True)
def db_engine():
    """No-op override of root conftest's SQLAlchemy engine fixture.

    See the docstring on `client` for the rationale.
    """
    yield None
