"""
Application configuration as module-level constants.

The values are resolved once, by ``app_settings.Settings`` (typed, validated):
``load_env.py`` overrides > process environment (``.env`` included) >
defaults. Code imports the constants from here.
"""

import os
import socket

from dotenv import load_dotenv

from upstage_backend.global_config.logger import logger
from upstage_backend.global_config.app_settings import (
    Settings,
    load_env_overrides,
    settings_kwargs,
)

# Into os.environ, so the direct os.getenv() readers elsewhere
# (STRICT_DB_CONTEXT, EVENT_ARCHIVE_*, ...) see .env values too.
load_dotenv()

# `load_env.py` is a machine-specific, git-ignored overrides file generated at
# install time (installation/phases/45_sync_load_env.sh) and present only on
# deployed hosts. It is absent in CI and on fresh checkouts, where the process
# environment alone applies. The GitHub pipeline must never depend on local vars.
_overrides = load_env_overrides()
if not _overrides:
    logger.info("load_env.py not present or empty; using environment configuration only")

settings = Settings(**settings_kwargs(_overrides))

# Fixed values (not configurable through the environment).
ALGORITHM = "HS256"
JWT_HEADER_NAME = "X-Access-Token"
EMAIL_TIME_TRIGGER_SECONDS = 60 * 1  # 1 minute
STREAM_EXPIRY_DAYS = 180
VIDEO_MAX_SIZE = 500 * 1024 * 1024  # KB
OTHER_MEDIA_MAX_SIZE = 500 * 1024 * 1024  # KB
ORIG_HOSTNAME = os.environ.get("HARDCODED_HOSTNAME") or socket.gethostname()

ENV_TYPE = settings.ENV_TYPE

DATABASE_CONNECT = settings.DATABASE_CONNECT
DATABASE_HOST = settings.DATABASE_HOST
DATABASE_PORT = settings.DATABASE_PORT
DATABASE_USER = settings.DATABASE_USER
DATABASE_PASSWORD = settings.DATABASE_PASSWORD
DATABASE_NAME = settings.DATABASE_NAME

STRIPE_KEY = settings.STRIPE_KEY
STRIPE_PRODUCT_ID = settings.STRIPE_PRODUCT_ID

SECRET_KEY = settings.SECRET_KEY
JWT_ADMIN_TOKEN_DAYS = settings.JWT_ADMIN_TOKEN_DAYS
JWT_USER_TOKEN_DAYS = settings.JWT_USER_TOKEN_DAYS

APPLE_ACCESS_TOKEN_CREATE = settings.APPLE_ACCESS_TOKEN_CREATE
APPLE_APP_ID = settings.APPLE_APP_ID
APPLE_APP_SECRET = settings.APPLE_APP_SECRET
APPLE_TEAM_ID = settings.APPLE_TEAM_ID

CLOUDFLARE_CAPTCHA_SECRETKEY = settings.CLOUDFLARE_CAPTCHA_SECRETKEY
CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT = settings.CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT

HOSTNAME = settings.HOSTNAME
logger.info("Hostname is: {}", HOSTNAME)
DOMAIN = settings.DOMAIN
UPSTAGE_FRONTEND_URL = settings.UPSTAGE_FRONTEND_URL

EMAIL_HOST = settings.EMAIL_HOST
EMAIL_PORT = settings.EMAIL_PORT
EMAIL_USE_TLS = settings.EMAIL_USE_TLS
EMAIL_HOST_FROM = settings.EMAIL_HOST_FROM
EMAIL_HOST_LOGIN = settings.EMAIL_HOST_LOGIN
EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD
EMAIL_HOST_DISPLAY_NAME = settings.EMAIL_HOST_DISPLAY_NAME
SUPPORT_EMAILS = settings.SUPPORT_EMAILS

STREAM_KEY = settings.STREAM_KEY

MQTT_BROKER = settings.MQTT_BROKER
MQTT_ADMIN_PORT = settings.MQTT_ADMIN_PORT
MQTT_TRANSPORT = settings.MQTT_TRANSPORT
MQTT_ADMIN_USER = settings.MQTT_ADMIN_USER
MQTT_ADMIN_PASSWORD = settings.MQTT_ADMIN_PASSWORD
MQTT_USER = settings.MQTT_USER
MQTT_PASSWORD = settings.MQTT_PASSWORD
PERFORMANCE_TOPIC_RULE = settings.PERFORMANCE_TOPIC_RULE

EVENT_COLLECTION = settings.EVENT_COLLECTION

CLIENT_MAX_BODY_SIZE = settings.CLIENT_MAX_BODY_SIZE

UPLOAD_USER_CONTENT_FOLDER = settings.UPLOAD_USER_CONTENT_FOLDER
DEMO_MEDIA_FOLDER = settings.DEMO_MEDIA_FOLDER

# Everything else load_env.py defines (names this module does not know, or
# replacements for the fixed values above) is exported as-is, exactly as the
# former `from .load_env import *` did.
globals().update(
    {name: value for name, value in _overrides.items() if name not in Settings.model_fields}
)

# Browsers get their broker credential from `Stage.mqtt` at runtime and have no
# build-time fallback (by design — a Vite fallback would re-inline the secret).
# A deployed host missing these would therefore hand every client a null
# credential and silently take MQTT down, so say so at boot. Only checked on the
# deployed environments; CI and local checkouts legitimately run without them.
if ENV_TYPE in ("Dev", "Production") and not (MQTT_USER and MQTT_PASSWORD):
    logger.error(
        "MQTT_USER/MQTT_PASSWORD are not configured; Stage.mqtt will return null "
        "and no browser will be able to connect to the broker. Set them in load_env.py."
    )

if not SECRET_KEY:
    if ENV_TYPE in ("Dev", "Production"):
        raise RuntimeError(
            "SECRET_KEY is not configured. Set it in load_env.py (deployed hosts) or the "
            "SECRET_KEY environment variable; refusing to start with no JWT signing key."
        )
    # CI / local checkouts: a random per-process key keeps tests self-contained
    # without ever falling back to a known value.
    import secrets as _secrets

    SECRET_KEY = _secrets.token_urlsafe(48)
    logger.warning(
        "SECRET_KEY is not configured; using a random per-process key (ENV_TYPE={}). "
        "Issued tokens will not survive a restart.",
        ENV_TYPE,
    )


def with_psycopg2_driver(url: str) -> str:
    """
    Name the sync driver explicitly on Postgres URLs.

    A driver-less ``postgresql://`` URL means "SQLAlchemy's default driver",
    which changed from psycopg2 to psycopg (v3) in SQLAlchemy 2.1 — an
    unpinned CI install then fails with ``No module named 'psycopg'``
    (2026-09-27). psycopg2-binary is the driver this app ships with, so say
    so. ``postgres://`` (Heroku-style) is no longer accepted by SQLAlchemy
    at all and is mapped the same way. URLs that already name a driver, and
    non-Postgres URLs, are returned unchanged.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url


if DATABASE_CONNECT:
    DATABASE_URL = f"{DATABASE_CONNECT}://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
else:
    # No DB parts configured (CI / DB-free unit tests): honor a full
    # DATABASE_URL from the environment, defaulting to in-memory SQLite.
    DATABASE_URL = settings.DATABASE_URL
DATABASE_URL = with_psycopg2_driver(DATABASE_URL)
