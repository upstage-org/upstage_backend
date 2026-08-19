"""Registration input validation (CreateUserInput).

Pure-pydantic tests, no DB. Regression coverage for the Aug 2026 prod
incident: a 1342-character Cyrillic intro was accepted at registration
(which then never validated at all) but crashed the admin activation
toggle, whose UpdateUserInput capped intro at 500 characters. The two
models must accept the same intro range, counted in characters not bytes.
"""

import pytest
from pydantic import ValidationError

from upstage_backend.studio_management.http.validation import UpdateUserInput
from upstage_backend.users.http.validation import CreateUserInput, format_validation_error

INTRO_MAX = 5000


def valid_payload(**overrides):
    payload = {
        "username": "testplayer",
        "password": "testpassword",
        "email": "player@example.org",
        "firstName": "Test",
        "lastName": "Player",
        "intro": "I am a test player.",
        "token": "testtoken",
    }
    payload.update(overrides)
    return payload


def update_payload(**overrides):
    payload = {
        "id": 1,
        "username": "testplayer",
        "email": "player@example.org",
        "role": 4,
        "active": True,
        "uploadLimit": 1,
    }
    payload.update(overrides)
    return payload


class TestCreateUserInput:
    def test_valid_payload_accepted(self):
        user = CreateUserInput(**valid_payload())
        assert user.username == "testplayer"

    def test_long_cyrillic_intro_accepted_by_create_and_update(self):
        # Mimics the real prod intro: 1342 characters, multibyte at the start.
        intro = "Привет! " + "х" * 1334
        assert len(intro) == 1342
        assert CreateUserInput(**valid_payload(intro=intro)).intro == intro
        assert UpdateUserInput(**update_payload(intro=intro)).intro == intro

    def test_intro_limits_match_between_create_and_update(self):
        at_limit = "y" * INTRO_MAX
        assert CreateUserInput(**valid_payload(intro=at_limit)).intro == at_limit
        assert UpdateUserInput(**update_payload(intro=at_limit)).intro == at_limit
        with pytest.raises(ValidationError):
            CreateUserInput(**valid_payload(intro="y" * (INTRO_MAX + 1)))
        with pytest.raises(ValidationError):
            UpdateUserInput(**update_payload(intro="y" * (INTRO_MAX + 1)))

    def test_intro_required(self):
        with pytest.raises(ValidationError):
            CreateUserInput(**valid_payload(intro=""))
        payload = valid_payload()
        del payload["intro"]
        with pytest.raises(ValidationError):
            CreateUserInput(**payload)

    def test_email_required_and_validated(self):
        payload = valid_payload()
        del payload["email"]
        with pytest.raises(ValidationError):
            CreateUserInput(**payload)
        with pytest.raises(ValidationError):
            CreateUserInput(**valid_payload(email="not-an-email"))

    def test_long_usernames_accepted(self):
        # Existing prod usernames run past the stale max_length=10
        # this model used to (dormantly) declare.
        name = "KostiantynPetrochenko"
        assert len(name) == 21
        assert CreateUserInput(**valid_payload(username=name)).username == name

    def test_username_bounds(self):
        with pytest.raises(ValidationError):
            CreateUserInput(**valid_payload(username="x"))
        with pytest.raises(ValidationError):
            CreateUserInput(**valid_payload(username="x" * 101))

    def test_token_and_names_optional(self):
        # The registration form sends token: null outside Production and
        # does not require first/last name.
        payload = valid_payload(token=None)
        del payload["firstName"]
        del payload["lastName"]
        user = CreateUserInput(**payload)
        assert user.token is None
        assert user.firstName is None

    def test_model_dump_keeps_service_contract(self):
        # UserService.create consumes a plain dict and does
        # data["token"] / del data["token"] / data.get("email", "").
        data = CreateUserInput(**valid_payload()).model_dump()
        assert data["token"] == "testtoken"
        del data["token"]
        assert data.get("email", "") == "player@example.org"
        assert set(data) == {"username", "password", "email", "firstName", "lastName", "intro"}


class TestFormatValidationError:
    def test_friendly_labels_and_missing_fields(self):
        payload = valid_payload(intro="")
        del payload["email"]
        with pytest.raises(ValidationError) as exc_info:
            CreateUserInput(**payload)
        message = format_validation_error(exc_info.value)
        assert "Email: is required" in message
        assert "Introduction:" in message
        # No raw pydantic locations or internals leak through.
        assert "loc" not in message
