"""Upload-limit policy (DB-free).

Regression coverage for the 2026-09-05 report: a super admin was told
"your upload limit is 1 MB" for a 1.2 MB multiframe avatar frame even
though admins are meant to have the highest possible upload allowance,
and raising a player's limit must actually change what they can upload.

Contract under test (users.services.upload_limit):
  * admin / super admin -> no per-user cap; only the server-wide 500 MiB
    cap (FileHandling.validate_file_size, matching nginx's 500M) applies
  * player / guest      -> capped at upstage_user.upload_limit
                            (1 MiB by default, adjustable by an admin);
                            a NULL stored value IS the 1 MiB default
                            (2026-09-11: it used to lift the cap)
  * every upload mutation (uploadFile, uploadMedia, updateMedia) applies
    the same cap through enforce_upload_cap
"""

import asyncio
import base64
import os

import pytest
from graphql import GraphQLError
from pydantic import ValidationError

from upstage_backend.assets.services.asset import AssetService
from upstage_backend.files.file_handling import FileHandling
from upstage_backend.stages.http.validation import UpdateMediaInput, UploadMediaInput
from upstage_backend.stages.services.media import MediaService
from upstage_backend.studio_management.http.validation import UpdateUserInput
from upstage_backend.users.db_models.user import ADMIN, GUEST, PLAYER, SUPER_ADMIN, UserModel
from upstage_backend.users.services.upload_limit import (
    DEFAULT_PLAYER_UPLOAD_LIMIT,
    SERVER_UPLOAD_MAX,
    effective_upload_limit,
    enforce_upload_cap,
    per_user_upload_cap,
)

MIB = 1024 * 1024
ONE_POINT_TWO_MB = int(1.2 * MIB)


def _user(role, upload_limit=DEFAULT_PLAYER_UPLOAD_LIMIT):
    return UserModel(id=1, username="u", role=role, active=True, upload_limit=upload_limit)


class TestPolicy:
    def test_server_max_matches_nginx_500m(self):
        assert SERVER_UPLOAD_MAX == 500 * MIB

    @pytest.mark.parametrize("role", [ADMIN, SUPER_ADMIN])
    def test_admins_have_no_per_user_cap_regardless_of_stored_value(self, role):
        for stored in (None, DEFAULT_PLAYER_UPLOAD_LIMIT, 300 * MIB):
            assert per_user_upload_cap(role, stored) is None
            assert effective_upload_limit(role, stored) == SERVER_UPLOAD_MAX

    def test_admin_role_given_as_string_is_still_uncapped(self):
        # to_dict()/GraphQL round-trips can hand the role over as a string.
        assert per_user_upload_cap(str(SUPER_ADMIN), DEFAULT_PLAYER_UPLOAD_LIMIT) is None

    @pytest.mark.parametrize("role", [PLAYER, GUEST])
    def test_players_use_their_stored_limit(self, role):
        assert per_user_upload_cap(role, DEFAULT_PLAYER_UPLOAD_LIMIT) == MIB
        assert effective_upload_limit(role, DEFAULT_PLAYER_UPLOAD_LIMIT) == MIB
        assert effective_upload_limit(role, 2 * MIB) == 2 * MIB

    @pytest.mark.parametrize("role", [PLAYER, GUEST])
    def test_null_limit_is_the_1mb_default_not_uncapped(self, role):
        # 2026-09-11: a player whose row has upload_limit NULL (old accounts,
        # batch-created users) was effectively uncapped on the server and
        # told "500 MB" by whoami. NULL now reads as the column default.
        assert per_user_upload_cap(role, None) == DEFAULT_PLAYER_UPLOAD_LIMIT
        assert effective_upload_limit(role, None) == DEFAULT_PLAYER_UPLOAD_LIMIT

    def test_stored_limit_given_as_string_is_coerced(self):
        assert per_user_upload_cap(PLAYER, str(2 * MIB)) == 2 * MIB


class TestEnforceUploadCap:
    def test_admin_never_raises(self):
        for stored in (None, DEFAULT_PLAYER_UPLOAD_LIMIT):
            enforce_upload_cap(ADMIN, stored, SERVER_UPLOAD_MAX)

    def test_player_boundary(self):
        enforce_upload_cap(PLAYER, DEFAULT_PLAYER_UPLOAD_LIMIT, MIB)
        with pytest.raises(GraphQLError, match=r"^File size must be under 1MB\.$"):
            enforce_upload_cap(PLAYER, DEFAULT_PLAYER_UPLOAD_LIMIT, MIB + 1)

    def test_player_null_limit_raises_like_default(self):
        with pytest.raises(GraphQLError, match="File size must be under 1MB"):
            enforce_upload_cap(PLAYER, None, ONE_POINT_TWO_MB)

    def test_fractional_cap_is_not_truncated_in_the_message(self):
        # int(1.5 MiB / MiB) used to print "1MB" for a 1.5 MiB cap.
        with pytest.raises(GraphQLError, match="File size must be under 1.5MB"):
            enforce_upload_cap(PLAYER, int(1.5 * MIB), 2 * MIB)


class TestUploadEnforcement:
    """AssetService.upload_file with the disk write stubbed out."""

    @pytest.fixture
    def service(self, monkeypatch):
        service = AssetService()
        written = []

        def fake_upload(base64_payload, filename, absolute_path, storage_path, sub_path):
            written.append(filename)
            return os.path.join(sub_path, filename)

        monkeypatch.setattr(service.file_handing, "upload_file", fake_upload)
        service.written = written
        return service

    @staticmethod
    def _stub_size(monkeypatch, service, size):
        monkeypatch.setattr(service.file_handing, "get_file_size", lambda _b64: size)

    @pytest.mark.parametrize("role", [ADMIN, SUPER_ADMIN])
    def test_admin_uploads_above_1mb_and_up_to_server_max(self, service, monkeypatch, role):
        user = _user(role)  # stored limit is the 1 MiB default
        for size in (ONE_POINT_TWO_MB, 300 * MIB, SERVER_UPLOAD_MAX):
            self._stub_size(monkeypatch, service, size)
            result = service.upload_file(user, "data:image/png;base64,AAAA", "frame.png")
            assert result["url"].endswith("frame.png")
        assert len(service.written) == 3

    def test_admin_is_still_bound_by_server_wide_cap(self):
        # The stubbed service above bypasses validate_file_size; prove the
        # real cap separately, at the exact boundary.
        FileHandling().validate_file_size(".png", SERVER_UPLOAD_MAX)
        with pytest.raises(GraphQLError, match="Image files must be under 500MB"):
            FileHandling().validate_file_size(".png", SERVER_UPLOAD_MAX + 1)
        with pytest.raises(GraphQLError, match="Video files must be under 500MB"):
            FileHandling().validate_file_size(".mp4", SERVER_UPLOAD_MAX + 1)

    def test_player_default_limit_rejects_1_2mb(self, service, monkeypatch):
        user = _user(PLAYER)
        self._stub_size(monkeypatch, service, ONE_POINT_TWO_MB)
        with pytest.raises(GraphQLError, match="File size must be under 1MB"):
            service.upload_file(user, "data:image/png;base64,AAAA", "frame.png")
        assert service.written == []

    def test_player_default_limit_accepts_files_up_to_1mb(self, service, monkeypatch):
        user = _user(PLAYER)
        self._stub_size(monkeypatch, service, MIB)
        service.upload_file(user, "data:image/png;base64,AAAA", "frame.png")
        assert service.written == ["frame.png"]

    def test_player_limit_increase_then_decrease(self, service, monkeypatch):
        user = _user(PLAYER)
        self._stub_size(monkeypatch, service, ONE_POINT_TWO_MB)

        # No change: default 1 MiB -> rejected.
        with pytest.raises(GraphQLError):
            service.upload_file(user, "data:image/png;base64,AAAA", "frame.png")

        # Admin raises the limit to 2 MiB -> accepted.
        user.upload_limit = 2 * MIB
        service.upload_file(user, "data:image/png;base64,AAAA", "frame.png")
        assert service.written == ["frame.png"]

        # Admin puts it back to 1 MiB -> rejected again.
        user.upload_limit = DEFAULT_PLAYER_UPLOAD_LIMIT
        with pytest.raises(GraphQLError, match="File size must be under 1MB"):
            service.upload_file(user, "data:image/png;base64,AAAA", "frame.png")
        assert service.written == ["frame.png"]

    def test_real_size_measurement_is_decoded_bytes(self):
        payload = b"x" * ONE_POINT_TWO_MB
        b64 = "data:image/png;base64," + base64.b64encode(payload).decode()
        assert FileHandling().get_file_size(b64) == ONE_POINT_TWO_MB


class TestMediaServicePathsAreCapped:
    """
    uploadMedia and updateMedia (replacement file / multiframe frames) write
    through FileHandling directly and used to skip the per-user cap
    entirely. The cap must fire before validate_asset_type / any DB access,
    so these run with no session at all: reaching the DB would itself fail.
    """

    @pytest.fixture
    def service(self, monkeypatch):
        service = MediaService()
        monkeypatch.setattr(service.file_handling, "get_file_size", lambda _b64: ONE_POINT_TWO_MB)

        def explode(*_args, **_kwargs):
            raise AssertionError("must be refused before touching the DB or disk")

        monkeypatch.setattr(service.asset_service, "validate_asset_type", explode)
        monkeypatch.setattr(service.file_handling, "upload_file", explode)
        monkeypatch.setattr(service.file_handling, "write_file", explode)
        return service

    def test_upload_media_refuses_over_limit_player(self, service):
        payload = UploadMediaInput(
            name="big", base64="data:image/png;base64,AAAA", mediaType="avatar", filename="big.png"
        )
        with pytest.raises(GraphQLError, match="File size must be under 1MB"):
            asyncio.run(service.upload_media(_user(PLAYER), payload))

    def test_update_media_refuses_over_limit_replacement_file(self, service):
        payload = UpdateMediaInput(id=1, name="x", base64="data:image/png;base64,AAAA")
        with pytest.raises(GraphQLError, match="File size must be under 1MB"):
            asyncio.run(service.update_media(payload, _user(PLAYER)))

    def test_update_media_refuses_over_limit_frame(self, service):
        payload = UpdateMediaInput(id=1, name="x", uploadedFrames=["data:image/png;base64,AAAA"])
        with pytest.raises(GraphQLError, match="File size must be under 1MB"):
            asyncio.run(service.update_media(payload, _user(PLAYER, upload_limit=None)))

    def test_update_media_without_payloads_does_not_measure_anything(self, service, monkeypatch):
        # No file, no frames: nothing to cap. Make get_file_size explode to
        # prove it is never consulted, then let validate_asset_type stop
        # the call before the DB.
        def never_measure(_b64):
            raise AssertionError("get_file_size must not run without a payload")

        monkeypatch.setattr(service.file_handling, "get_file_size", never_measure)
        with pytest.raises(AssertionError, match="before touching"):
            asyncio.run(service.update_media(UpdateMediaInput(id=1, name="x"), _user(PLAYER)))


class TestUpdateUserInput:
    def _payload(self, **overrides):
        payload = {
            "id": 1,
            "username": "admin",
            "email": "admin@example.org",
            "role": SUPER_ADMIN,
            "active": True,
        }
        payload.update(overrides)
        return payload

    def test_upload_limit_may_be_omitted(self):
        # The SPA drops null variables (userGraph.updateUser omits nil), so a
        # user whose stored limit is NULL (migration-seeded admin) sends no
        # uploadLimit at all; that must not make the whole update invalid.
        assert UpdateUserInput(**self._payload()).uploadLimit is None

    def test_upload_limit_accepts_an_integer(self):
        assert UpdateUserInput(**self._payload(uploadLimit=2 * MIB)).uploadLimit == 2 * MIB

    def test_upload_limit_rejects_non_integer(self):
        with pytest.raises(ValidationError):
            UpdateUserInput(**self._payload(uploadLimit="lots"))
