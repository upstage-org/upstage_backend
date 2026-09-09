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

import os
import re
import time

import pytest

REAL_DB_OPT_IN = "UPSTAGE_TESTS_ALLOW_REAL_DB"

# The src-tree integration tests call get_session() directly (outside any
# HTTP request), which strict db-context mode forbids. The e2e container
# runs with STRICT_DB_CONTEXT=0; mirror that for every pytest session so
# the suite behaves identically on the host. (The tests/ subtree conftests
# set it too; setdefault keeps any explicit operator override in force.)
os.environ.setdefault("STRICT_DB_CONTEXT", "0")

_SRC_TESTS_PATH_FRAGMENT = f"{os.sep}src{os.sep}upstage_backend{os.sep}"


def _collected_src_integration_tests(request):
    """
    True when the collected session includes tests from the src tree
    (src/upstage_backend/**/tests). Those are the ones that write through the
    live app into the configured database; the `tests/` suites rebind to
    SQLite per-test and are safe regardless of DATABASE_URL.
    """
    for item in request.session.items:
        path = str(getattr(item, "fspath", "") or "")
        if _SRC_TESTS_PATH_FRAGMENT in path:
            return True
    return False


def pytest_collection_modifyitems(session, config, items):
    """
    When the real-DB opt-in is set but the configured database is
    unreachable (e.g. running on the host, outside the compose network),
    skip the src-tree integration tests with a clear reason instead of
    letting every one of them error. The sqlite-bound `tests/` suites are
    unaffected. Without the opt-in the hard pytest.exit safety guard in
    _guard_against_real_db still applies.
    """
    if os.environ.get(REAL_DB_OPT_IN) != "1":
        return
    src_items = [item for item in items if _SRC_TESTS_PATH_FRAGMENT in str(item.fspath)]
    if not src_items:
        return

    from upstage_backend.global_config import env

    if env.DATABASE_URL.startswith("sqlite"):
        return
    try:
        from sqlalchemy import create_engine

        probe = create_engine(env.DATABASE_URL, connect_args={"connect_timeout": 3})
        with probe.connect():
            pass
        probe.dispose()
    except Exception:
        location = env.DATABASE_URL.rsplit("@", 1)[-1]
        marker = pytest.mark.skip(
            reason=f"configured database ({location}) is unreachable from this host; "
            "src-tree integration tests need it (run inside the compose network)"
        )
        for item in src_items:
            item.add_marker(marker)


def _guard_against_real_db(request):
    """
    Abort the test session when src-tree integration tests are about to run
    against a real database without an explicit opt-in.

    The src-tree integration tests (auth_test.py, test_stage.py, ...) INSERT
    rows through the live app: faker users, public "Stage Name" stages, test
    assets. `load_env.py` hardcodes DATABASE_URL to the dev Postgres, so a
    plain `pytest` inside the compose network used to litter dev — 37 leftover
    stages were visible as empty panels in the public foyer (cleaned up
    2026-07-09). Set UPSTAGE_TESTS_ALLOW_REAL_DB=1 to run anyway; the
    `_sweep_test_fixtures` teardown then deletes the reserved-pattern rows
    (@example.* users and everything they own) when the session ends.
    """
    if not _collected_src_integration_tests(request):
        return
    if os.environ.get(REAL_DB_OPT_IN) == "1":
        return
    from upstage_backend.global_config import env

    if env.DATABASE_URL.startswith("sqlite"):
        return
    location = env.DATABASE_URL.rsplit("@", 1)[-1]
    pytest.exit(
        f"Refusing to run the src-tree integration tests against a real database ({location}). "
        "These tests insert faker users and public 'Stage Name' stages into "
        "whatever database the app is configured for. "
        f"Set {REAL_DB_OPT_IN}=1 to opt in (leftover test rows are swept at teardown).",
        returncode=3,
    )


def _sweep_test_fixtures(engine):
    """
    Delete rows the integration tests create, identified by the reserved
    example.com/org/net domains (RFC 2606 — never real users): the faker
    users themselves and everything they own (stages, attributes, assets,
    sessions). Runs only for real-DB sessions (see _guard_against_real_db).
    """
    import json

    from sqlalchemy import text

    from upstage_backend.global_config import logger
    from upstage_backend.global_config.env import UPLOAD_USER_CONTENT_FOLDER

    statements = [
        """CREATE TEMP TABLE _sweep_users AS SELECT id FROM upstage_user
           WHERE email LIKE '%@example.com' OR email LIKE '%@example.org'
              OR email LIKE '%@example.net' OR username LIKE '%@example.%'""",
        """CREATE TEMP TABLE _sweep_stages AS SELECT id FROM stage
           WHERE owner_id IN (SELECT id FROM _sweep_users)""",
        """CREATE TEMP TABLE _sweep_assets AS SELECT id FROM asset
           WHERE owner_id IN (SELECT id FROM _sweep_users)""",
        # Live events are keyed by topic (= the stage slug), not only by
        # performance: the "Stage Name"/"doomed…" fixtures left topic rows
        # like '/path/to/file/' behind on dev (2026-09-10).
        """DELETE FROM events WHERE topic LIKE ANY
           (SELECT '%/' || file_location || '/%' FROM stage
             WHERE id IN (SELECT id FROM _sweep_stages))""",
        "DELETE FROM media_tag WHERE asset_id IN (SELECT id FROM _sweep_assets)",
        "DELETE FROM asset_attribute WHERE asset_id IN (SELECT id FROM _sweep_assets)",
        """DELETE FROM parent_stage WHERE stage_id IN (SELECT id FROM _sweep_stages)
           OR child_asset_id IN (SELECT id FROM _sweep_assets)""",
        "DELETE FROM stage_attribute WHERE stage_id IN (SELECT id FROM _sweep_stages)",
        "DELETE FROM scene WHERE stage_id IN (SELECT id FROM _sweep_stages)",
        """DELETE FROM events WHERE performance_id IN
           (SELECT id FROM performance WHERE stage_id IN (SELECT id FROM _sweep_stages))""",
        "DELETE FROM performance WHERE stage_id IN (SELECT id FROM _sweep_stages)",
        "DELETE FROM stage WHERE id IN (SELECT id FROM _sweep_stages)",
        "DELETE FROM asset WHERE id IN (SELECT id FROM _sweep_assets)",
        "DELETE FROM user_session WHERE user_id IN (SELECT id FROM _sweep_users)",
        "DELETE FROM admin_one_time_totp_qr_url WHERE user_id IN (SELECT id FROM _sweep_users)",
        "DELETE FROM upstage_user WHERE id IN (SELECT id FROM _sweep_users)",
    ]
    try:
        with engine.begin() as connection:
            connection.execute(text(statements[0]))
            connection.execute(text(statements[1]))
            connection.execute(text(statements[2]))
            # Uploaded files of swept assets (test.png copies under image/,
            # media/, avatar/ …) are only removable while the rows still exist.
            file_locations = []
            for location, description in connection.execute(
                text(
                    "SELECT file_location, description FROM asset"
                    " WHERE id IN (SELECT id FROM _sweep_assets)"
                )
            ).fetchall():
                file_locations.append(location)
                # Multi-frame media keep extra files listed in the description.
                try:
                    frames = (json.loads(description or "{}") or {}).get("frames") or []
                except (TypeError, ValueError):
                    frames = []
                file_locations.extend(f for f in frames if isinstance(f, str))
            # Users created by the tests were appended to every default
            # stage's playerAccess by assign_user_to_default_stage; strip
            # those ids so the JSON does not accumulate dangling entries.
            swept_ids = {
                str(row[0]) for row in connection.execute(text("SELECT id FROM _sweep_users"))
            }
            for attr_id, description in connection.execute(
                text("SELECT id, description FROM stage_attribute WHERE name = 'playerAccess'")
            ).fetchall():
                try:
                    accesses = json.loads(description or "")
                except (TypeError, ValueError):
                    continue
                if not isinstance(accesses, list):
                    continue
                trimmed = [
                    [uid for uid in group if str(uid) not in swept_ids]
                    if isinstance(group, list)
                    else group
                    for group in accesses
                ]
                if trimmed != accesses:
                    connection.execute(
                        text("UPDATE stage_attribute SET description = :d WHERE id = :i"),
                        {"d": json.dumps(trimmed), "i": attr_id},
                    )
            for statement in statements[3:]:
                connection.execute(text(statement))
        upload_root = os.path.realpath(UPLOAD_USER_CONTENT_FOLDER)
        for location in file_locations:
            if not location or "://" in location:
                continue
            path = os.path.realpath(os.path.join(upload_root, location))
            if path.startswith(upload_root + os.sep) and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    logger.warning("Could not remove swept test upload {}".format(path))
        logger.info("Swept @example.* test fixtures from the database")
    except Exception:
        logger.exception("Failed to sweep test fixtures; leftover rows may remain")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def client(request):
    _guard_against_real_db(request)

    from starlette.testclient import TestClient

    from upstage_backend.global_config import logger
    from upstage_backend.main import app

    with TestClient(app=app, base_url="http://localhost:8000") as test_client:
        logger.info("Client is ready")
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def db_engine(request):
    _guard_against_real_db(request)

    from sqlalchemy import create_engine, text

    from upstage_backend.global_config import env, logger

    engine = create_engine(env.DATABASE_URL)
    yield engine
    start_time = time.time()
    # Sweep + terminate only when a real-Postgres integration session actually
    # ran; a sqlite-only session (tests/unit, tests/event_archive_tests) must
    # not reach out to the configured Postgres at teardown — off the compose
    # network that host is not even resolvable.
    ran_real_db_integration = not env.DATABASE_URL.startswith(
        "sqlite"
    ) and _collected_src_integration_tests(request)
    if ran_real_db_integration:
        _sweep_test_fixtures(engine)
    engine.dispose()
    if not ran_real_db_integration:
        return
    from sqlalchemy.exc import OperationalError

    # Terminating every backend is only appropriate on a throwaway database
    # (CI drops it next). On a shared dev database it severs the live API's
    # connection pool and every open browser session mid-request.
    if not re.search(r"(_e2e|_test|test_)", env.DATABASE_NAME or ""):
        logger.warning(
            "Not terminating backends of shared database %s (only *_e2e/*_test databases)",
            env.DATABASE_NAME,
        )
        return
    try:
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
    except OperationalError:
        logger.warning("Database unreachable at teardown; skipped terminating leftover backends")
    end_time = time.time()
    logger.info(f"Time taken to drop all tables: {end_time - start_time} seconds")
