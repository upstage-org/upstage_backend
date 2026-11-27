"""
CI 2026-09-27: `alembic upgrade head` failed with `No module named 'psycopg'`
because a driver-less `postgresql://` URL selects SQLAlchemy's default
Postgres driver, which is psycopg (v3) from SQLAlchemy 2.1 on. The app ships
psycopg2, so the URL must name it.
"""

import pytest

from upstage_backend.global_config.env import with_psycopg2_driver


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        ("postgres://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
    ],
)
def test_with_psycopg2_driver(given, expected):
    assert with_psycopg2_driver(given) == expected
