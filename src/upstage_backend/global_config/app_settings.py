"""
Typed application settings.

Values come from, highest priority first:

1. ``load_env.py`` - the machine-specific, git-ignored overrides module the
   installer generates on deployed hosts (absent in CI and fresh checkouts);
2. the process environment (``.env`` is loaded into it by ``env.py``);
3. the defaults declared here.

``env.py`` instantiates :class:`Settings` once and re-exports every field as a
module-level constant, which is what the rest of the code imports.
"""

import socket
from importlib import import_module
from typing import Annotated, Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _mangled_hostname() -> str:
    return socket.gethostname().replace(".", "_").replace("-", "_")


class Settings(BaseSettings):
    # extra="allow": load_env.py also carries names this app no longer reads
    # (MONGO_*, CIPHER_KEY, ...); they are kept and re-exported, not rejected.
    model_config = SettingsConfigDict(case_sensitive=True, extra="allow")

    ENV_TYPE: str = "development"

    DATABASE_CONNECT: str | None = None
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int | str | None = None
    DATABASE_USER: str | None = None
    DATABASE_PASSWORD: str | None = None
    DATABASE_NAME: str | None = None
    # Full URL, used only when DATABASE_CONNECT is not set (CI / DB-free unit
    # tests); defaults to in-memory SQLite.
    DATABASE_URL: str = "sqlite:///:memory:"

    # payment
    STRIPE_KEY: str = ""
    STRIPE_PRODUCT_ID: str = ""

    # JWT. No built-in default: env.py refuses an unset key on deployed hosts,
    # so a checkout that forgot its load_env.py can never sign tokens with a
    # publicly known secret.
    SECRET_KEY: str = ""
    # How long a login lasts, in days, by role: admins and super admins /
    # everyone else. Applies to the access token and to the refresh token
    # issued with it (see AuthenticationService.token_lifetime).
    JWT_ADMIN_TOKEN_DAYS: int = Field(default=30, gt=0)
    JWT_USER_TOKEN_DAYS: int = Field(default=2, gt=0)

    # Apple
    APPLE_ACCESS_TOKEN_CREATE: str | None = None
    APPLE_APP_ID: str | None = None
    APPLE_APP_SECRET: str | None = None
    APPLE_TEAM_ID: str | None = None

    CLOUDFLARE_CAPTCHA_SECRETKEY: str | None = None
    CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT: str | None = None

    # The HOSTNAME environment variable is deliberately not read: the value is
    # HARDCODED_HOSTNAME when set, else this machine's name with "." and "-"
    # replaced by "_" (it is used as an identifier). The alias is therefore
    # the only name the field can be set by (see settings_kwargs).
    HOSTNAME: str = Field(
        default_factory=_mangled_hostname,
        validation_alias=AliasChoices("HARDCODED_HOSTNAME"),
    )
    DOMAIN: str = "upstage.live"
    UPSTAGE_FRONTEND_URL: str = "http://localhost:3000"

    EMAIL_HOST: str | None = None
    EMAIL_PORT: int = 465
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_FROM: str | None = None
    EMAIL_HOST_LOGIN: str | None = None
    EMAIL_HOST_PASSWORD: str | None = None
    EMAIL_HOST_DISPLAY_NAME: str = "UpStage"
    # Comma-separated in the environment.
    SUPPORT_EMAILS: Annotated[list[str], NoDecode] = ["support@upstage.live"]

    STREAM_KEY: str = ""

    MQTT_BROKER: str | None = None
    MQTT_ADMIN_PORT: int = 1883
    MQTT_TRANSPORT: str = "tcp"
    MQTT_ADMIN_USER: str | None = None
    MQTT_ADMIN_PASSWORD: str | None = None
    # Browser-facing broker account. Served to clients at runtime on
    # `Stage.mqtt` so the credential is not compiled into the frontend bundle.
    MQTT_USER: str | None = None
    MQTT_PASSWORD: str | None = None
    PERFORMANCE_TOPIC_RULE: str = "#"

    EVENT_COLLECTION: str | None = None

    CLIENT_MAX_BODY_SIZE: int = 0

    UPLOAD_USER_CONTENT_FOLDER: str = "/usr/app/uploads"  # mounted by docker-compose
    DEMO_MEDIA_FOLDER: str = "./dashboard/demo"

    @field_validator("SUPPORT_EMAILS", mode="before")
    @classmethod
    def _split_support_emails(cls, value: Any) -> Any:
        return value.split(",") if isinstance(value, str) else value


def settings_kwargs(overrides: dict[str, Any]) -> dict[str, Any]:
    """The overrides that are Settings fields, keyed the way Settings accepts them."""
    kwargs = {name: value for name, value in overrides.items() if name in Settings.model_fields}
    if "HOSTNAME" in kwargs:
        kwargs["HARDCODED_HOSTNAME"] = kwargs.pop("HOSTNAME")
    return kwargs


def load_env_overrides() -> dict[str, Any]:
    """
    The public names of ``load_env.py`` (what ``from .load_env import *``
    used to bring in), or ``{}`` when the module does not exist.
    """
    try:
        module = import_module("upstage_backend.global_config.load_env")
    except ModuleNotFoundError as error:
        if error.name != "upstage_backend.global_config.load_env":
            raise
        return {}
    names = getattr(module, "__all__", None)
    if names is None:
        names = [name for name in vars(module) if not name.startswith("_")]
    return {name: getattr(module, name) for name in names}
