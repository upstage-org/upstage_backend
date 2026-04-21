# -*- coding: iso8859-15 -*-
"""
Async SQLAlchemy session for the event_archive service.

Builds a dedicated async engine (postgresql+asyncpg) derived from the sync
DATABASE_URL used by the web app, so the existing synchronous engine in
global_config/database.py is untouched. All writer tasks share a single
connection pool via AsyncSessionLocal.
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

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from global_config.env import DATABASE_URL


def _to_async_url(sync_url: str) -> str:
    """
    Rewrite a sync SQLAlchemy URL (postgresql://... or postgres://...) to use
    the asyncpg driver. Leaves already-async URLs alone.
    """
    if sync_url.startswith("postgresql+asyncpg://"):
        return sync_url
    if sync_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + sync_url[len("postgresql://") :]
    if sync_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + sync_url[len("postgres://") :]
    return sync_url


ASYNC_DATABASE_URL = _to_async_url(DATABASE_URL)

_POOL_SIZE = int(os.getenv("EVENT_ARCHIVE_DB_POOL_SIZE", "5"))
_MAX_OVERFLOW = int(os.getenv("EVENT_ARCHIVE_DB_MAX_OVERFLOW", "5"))

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)
