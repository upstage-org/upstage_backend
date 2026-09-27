"""
global_config.app_settings: precedence (load_env.py overrides > environment >
defaults) and the few non-obvious parsing rules.
"""

import sys
import types

import pytest
from pydantic import ValidationError

from upstage_backend.global_config import app_settings as settings_module
from upstage_backend.global_config.app_settings import (
    Settings,
    load_env_overrides,
    settings_kwargs,
)

LOAD_ENV = "upstage_backend.global_config.load_env"


@pytest.fixture
def clean_env(monkeypatch):
    for name in list(Settings.model_fields) + ["HARDCODED_HOSTNAME", "HOSTNAME"]:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_without_any_configuration(clean_env):
    settings = Settings()
    assert settings.ENV_TYPE == "development"
    assert settings.DATABASE_URL == "sqlite:///:memory:"
    assert settings.SECRET_KEY == ""
    assert settings.EMAIL_PORT == 465
    assert settings.SUPPORT_EMAILS == ["support@upstage.live"]
    assert settings.CLIENT_MAX_BODY_SIZE == 0


def test_environment_values_are_typed(clean_env):
    clean_env.setenv("EMAIL_PORT", "587")
    clean_env.setenv("MQTT_ADMIN_PORT", "8883")
    clean_env.setenv("CLIENT_MAX_BODY_SIZE", "1048576")
    settings = Settings()
    assert settings.EMAIL_PORT == 587
    assert settings.MQTT_ADMIN_PORT == 8883
    assert settings.CLIENT_MAX_BODY_SIZE == 1048576


def test_support_emails_are_comma_separated(clean_env):
    clean_env.setenv("SUPPORT_EMAILS", "a@example.com,b@example.com")
    assert Settings().SUPPORT_EMAILS == ["a@example.com", "b@example.com"]


def test_a_malformed_value_fails_at_startup(clean_env):
    clean_env.setenv("EMAIL_PORT", "not-a-port")
    with pytest.raises(ValidationError):
        Settings()


def test_hostname_ignores_the_HOSTNAME_variable(clean_env):
    clean_env.setattr(settings_module.socket, "gethostname", lambda: "app-1.example.org")
    clean_env.setenv("HOSTNAME", "from-the-shell")
    assert Settings().HOSTNAME == "app_1_example_org"

    clean_env.setenv("HARDCODED_HOSTNAME", "dev.upstage.live")
    assert Settings().HOSTNAME == "dev.upstage.live"


def test_overrides_beat_the_environment(clean_env):
    clean_env.setenv("ENV_TYPE", "Test")
    clean_env.setenv("HARDCODED_HOSTNAME", "from-env")
    overrides = {"ENV_TYPE": "Production", "HOSTNAME": "from-load-env", "DATABASE_PORT": 5432}
    settings = Settings(**settings_kwargs(overrides))
    assert settings.ENV_TYPE == "Production"
    assert settings.HOSTNAME == "from-load-env"
    assert settings.DATABASE_PORT == 5432


def test_settings_kwargs_keeps_only_known_fields():
    kwargs = settings_kwargs({"STREAM_KEY": "k", "MONGO_HOST": "legacy", "CIPHER_KEY": b"x"})
    assert kwargs == {"STREAM_KEY": "k"}


def test_load_env_overrides_reads_public_names(monkeypatch):
    module = types.ModuleType(LOAD_ENV)
    module.STREAM_KEY = "k"
    module.CLIENT_MAX_BODY_SIZE = 5 * 1024
    module._private = "hidden"
    monkeypatch.setitem(sys.modules, LOAD_ENV, module)
    assert load_env_overrides() == {"STREAM_KEY": "k", "CLIENT_MAX_BODY_SIZE": 5120}


def test_load_env_overrides_is_empty_without_the_module(monkeypatch):
    monkeypatch.delitem(sys.modules, LOAD_ENV, raising=False)

    def missing(name):
        raise ModuleNotFoundError(f"No module named {name!r}", name=name)

    monkeypatch.setattr(settings_module, "import_module", missing)
    assert load_env_overrides() == {}


def test_a_broken_import_inside_load_env_is_not_swallowed(monkeypatch):
    def broken(name):
        raise ModuleNotFoundError("No module named 'somethingelse'", name="somethingelse")

    monkeypatch.setattr(settings_module, "import_module", broken)
    with pytest.raises(ModuleNotFoundError):
        load_env_overrides()
