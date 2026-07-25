# -*- coding: iso8859-15 -*-
"""deleteUser content handling: DELETE_ALL wipes a user's stages, media and
recordings (substituting the placeholder into surviving references), while the
default REASSIGN_TO_ADMIN keeps only avatars/props/backdrops, handing them to
the canonical admin. Users here live on RFC-2606 example.com addresses so the
root-conftest sweep owns any leftovers."""

import json
import os
import random

import pytest

from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.assets.db_models.asset_usage import AssetUsageModel
from upstage_backend.assets.tests import asset_test
from upstage_backend.assets.tests.asset_test import load_base64_from_image
from upstage_backend.authentication.db_models.user_session import UserSessionModel
from upstage_backend.authentication.tests.auth_test import TestAuthenticationController
from upstage_backend.event_archive.db_models.event import EventModel
from upstage_backend.global_config import get_session
from upstage_backend.global_config.database import ScopedSession
from upstage_backend.global_config.env import (
    JWT_HEADER_NAME,
    UPLOAD_USER_CONTENT_FOLDER,
)
from upstage_backend.global_config.helpers.fernet_crypto import encrypt
from upstage_backend.performance_config.db_models.performance import PerformanceModel
from upstage_backend.performance_config.db_models.scene import SceneModel
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
from upstage_backend.stages.scripts.scaffold_base_media import (
    CANONICAL_ADMIN_USERNAME,
    PLACEHOLDER_FILE_LOCATION,
)
from upstage_backend.users.db_models.user import PLAYER, SUPER_ADMIN, UserModel

auth = TestAuthenticationController()

GRAPHQL = "/api/studio_graphql"
TEST_IMAGE = os.path.join(os.path.dirname(asset_test.__file__), "images", "test.png")

CREATE_STAGE = """
    mutation createStage($input: StageInput!) {
        createStage(input: $input) { id name fileLocation }
    }
"""

UPLOAD_MEDIA = """
    mutation uploadMedia($input: UploadMediaInput!) {
        uploadMedia(input: $input) { id }
    }
"""

ASSIGN_MEDIA = """
    mutation assignMedia($input: AssignMediaInput!) {
        assignMedia(input: $input) { id }
    }
"""

QUICK_ASSIGN = """
    mutation quickAssign($stageIds: [ID]!, $assetId: ID!) {
        quickAssignMutation(stageIds: $stageIds, assetId: $assetId) { success }
    }
"""

SAVE_SCENE = """
    mutation saveScene($input: SceneInput!) {
        saveScene(input: $input) { id }
    }
"""

START_RECORDING = """
    mutation startRecording($input: RecordInput!) {
        startRecording(input: $input) { id }
    }
"""

SAVE_RECORDING = """
    mutation saveRecording($id: ID!) {
        saveRecording(id: $id) { id }
    }
"""

DELETE_USER = """
    mutation DeleteUser($id: ID!, $contentAction: UserContentAction) {
        deleteUser(id: $id, contentAction: $contentAction) { success message }
    }
"""


def make_user(client, role=PLAYER):
    """Create + log in a sweep-owned user; returns (user_id, headers)."""
    email = "deluser{}@example.com".format(random.randint(1, 10**9))
    user = UserModel(
        username=email,
        password=encrypt("testpassword"),
        email=email,
        active=True,
        role=role,
    )
    with ScopedSession() as s:
        s.add(user)
        s.flush()
        user_id = user.id
    response = client.post(
        GRAPHQL,
        json={
            "query": auth.login_query,
            "variables": {"payload": {"username": email, "password": "testpassword"}},
        },
    )
    login = response.json()["data"]["login"]
    return user_id, {
        "Authorization": "Bearer {}".format(login["access_token"]),
        JWT_HEADER_NAME: login["refresh_token"],
    }


def gql(client, headers, query, variables=None):
    response = client.post(
        GRAPHQL, json={"query": query, "variables": variables or {}}, headers=headers
    )
    assert response.status_code == 200
    return response.json()


def create_stage(client, headers):
    slug = "doomed{}".format(random.randint(1, 10**9))
    data = gql(
        client,
        headers,
        CREATE_STAGE,
        {
            "input": {
                "fileLocation": slug,
                "status": "live",
                "visibility": False,
                "cover": "",
                "name": "Doomed Stage {}".format(slug),
                "description": "deleteUser test stage",
                "playerAccess": "[[],[]]",
                "config": None,
            }
        },
    )
    assert "errors" not in data, data
    return data["data"]["createStage"]


def upload_media(client, headers, name, media_type, filename=None):
    """uploadMedia + return (asset_id, file_location)."""
    data = gql(
        client,
        headers,
        UPLOAD_MEDIA,
        {
            "input": {
                "name": name,
                "mediaType": media_type,
                "filename": filename or "{}.png".format(name),
                "base64": "data:image/jpeg;base64,{}".format(load_base64_from_image(TEST_IMAGE)),
            }
        },
    )
    assert "errors" not in data, data
    asset_id = int(data["data"]["uploadMedia"]["id"])
    with ScopedSession() as s:
        location = s.query(AssetModel).filter_by(id=asset_id).first().file_location
    return asset_id, location


def record_board_events(client, headers, stage_id, file_location, payload_srcs):
    """startRecording, drop board events referencing the given media, save."""
    data = gql(
        client,
        headers,
        START_RECORDING,
        {"input": {"stageId": stage_id, "name": "Doomed show", "description": "t"}},
    )
    assert "errors" not in data, data
    performance_id = int(data["data"]["startRecording"]["id"])

    with ScopedSession() as session:
        for i, src in enumerate(payload_srcs):
            session.add(
                EventModel(
                    topic="/{}/board".format(file_location),
                    mqtt_timestamp=1000.0 + i,
                    payload={
                        "type": "placeObjectOnStage",
                        "object": {"src": "/resources/{}".format(src), "x": 0.5},
                    },
                )
            )
        session.flush()

    data = gql(client, headers, SAVE_RECORDING, {"id": performance_id})
    assert "errors" not in data, data
    return performance_id


def canonical_admin_id():
    with ScopedSession() as s:
        admin = s.query(UserModel).filter(UserModel.username == CANONICAL_ADMIN_USERNAME).first()
        return admin.id if admin else None


@pytest.mark.anyio
class TestDeleteUserContent:
    async def test_01_delete_all_wipes_everything(self, client):
        doomed_id, doomed_headers = make_user(client)

        stage = create_stage(client, doomed_headers)
        stage_id = int(stage["id"])
        stage_loc = stage["fileLocation"]

        media = {
            kind: upload_media(client, doomed_headers, "doomed-{}".format(kind), kind)
            for kind in ("backdrop", "avatar", "prop")
        }
        gql(
            client,
            doomed_headers,
            ASSIGN_MEDIA,
            {"input": {"id": stage_id, "mediaIds": [aid for aid, _ in media.values()]}},
        )

        scene_payload = json.dumps(
            {
                "background": "/resources/{}".format(media["backdrop"][1]),
                "objects": [
                    {"src": "/resources/{}".format(media["avatar"][1])},
                    {"src": "/resources/{}".format(media["prop"][1])},
                ],
            }
        )
        data = gql(
            client,
            doomed_headers,
            SAVE_SCENE,
            {
                "input": {
                    "stageId": stage_id,
                    "name": "Doomed scene",
                    "preview": "p",
                    "payload": scene_payload,
                }
            },
        )
        assert "errors" not in data, data

        performance_id = record_board_events(
            client,
            doomed_headers,
            stage_id,
            stage_loc,
            [media["avatar"][1], media["prop"][1]],
        )

        _, admin_headers = make_user(client, SUPER_ADMIN)
        data = gql(
            client,
            admin_headers,
            DELETE_USER,
            {"id": doomed_id, "contentAction": "DELETE_ALL"},
        )
        assert "errors" not in data, data
        assert data["data"]["deleteUser"]["success"]

        session = get_session()
        assert session.query(UserModel).filter_by(id=doomed_id).first() is None
        assert session.query(StageModel).filter_by(id=stage_id).first() is None
        assert session.query(StageAttributeModel).filter_by(stage_id=stage_id).count() == 0
        assert session.query(ParentStageModel).filter_by(stage_id=stage_id).count() == 0
        assert session.query(SceneModel).filter_by(stage_id=stage_id).count() == 0
        assert session.query(PerformanceModel).filter_by(stage_id=stage_id).count() == 0
        assert (
            session.query(EventModel).filter(EventModel.performance_id == performance_id).count()
            == 0
        )
        assert (
            session.query(EventModel)
            .filter(EventModel.topic.like("%/{}/%".format(stage_loc)))
            .count()
            == 0
        )
        for asset_id, location in media.values():
            assert session.query(AssetModel).filter_by(id=asset_id).first() is None
            assert not os.path.exists(os.path.join(UPLOAD_USER_CONTENT_FOLDER, location))
        assert session.query(AssetUsageModel).filter_by(user_id=doomed_id).count() == 0
        assert session.query(UserSessionModel).filter_by(user_id=doomed_id).count() == 0

    async def test_02_placeholder_substitution_on_surviving_content(self, client):
        doomed_id, doomed_headers = make_user(client)
        prop_id, prop_loc = upload_media(client, doomed_headers, "shared-prop", "prop")

        survivor_id, survivor_headers = make_user(client, SUPER_ADMIN)
        stage = create_stage(client, survivor_headers)
        stage_id = int(stage["id"])
        stage_loc = stage["fileLocation"]

        data = gql(
            client,
            survivor_headers,
            QUICK_ASSIGN,
            {"stageIds": [stage_id], "assetId": prop_id},
        )
        assert "errors" not in data, data

        data = gql(
            client,
            survivor_headers,
            SAVE_SCENE,
            {
                "input": {
                    "stageId": stage_id,
                    "name": "Survivor scene",
                    "preview": "p",
                    "payload": json.dumps({"objects": [{"src": "/resources/{}".format(prop_loc)}]}),
                }
            },
        )
        assert "errors" not in data, data

        performance_id = record_board_events(
            client, survivor_headers, stage_id, stage_loc, [prop_loc]
        )

        data = gql(
            client,
            survivor_headers,
            DELETE_USER,
            {"id": doomed_id, "contentAction": "DELETE_ALL"},
        )
        assert "errors" not in data, data

        session = get_session()
        placeholder = (
            session.query(AssetModel)
            .filter(AssetModel.file_location == PLACEHOLDER_FILE_LOCATION)
            .first()
        )
        assert placeholder is not None
        assert placeholder.owner_id == canonical_admin_id()
        assert os.path.exists(os.path.join(UPLOAD_USER_CONTENT_FOLDER, PLACEHOLDER_FILE_LOCATION))

        # The surviving stage keeps working: assignment re-pointed, payloads
        # rewritten, nothing else touched.
        assert session.query(AssetModel).filter_by(id=prop_id).first() is None
        links = session.query(ParentStageModel).filter_by(stage_id=stage_id).all()
        assert [link.child_asset_id for link in links] == [placeholder.id]

        scene = session.query(SceneModel).filter(SceneModel.stage_id == stage_id).first()
        assert PLACEHOLDER_FILE_LOCATION in scene.payload
        assert prop_loc not in scene.payload

        events = session.query(EventModel).filter(EventModel.performance_id == performance_id).all()
        assert events
        for event in events:
            serialized = json.dumps(event.payload)
            assert PLACEHOLDER_FILE_LOCATION in serialized
            assert prop_loc not in serialized

        assert session.query(StageModel).filter_by(id=stage_id).first() is not None
        assert session.query(UserModel).filter_by(id=survivor_id).first() is not None

    async def test_03_reassign_keeps_only_avatars_props_backdrops(self, client):
        doomed_id, doomed_headers = make_user(client)
        stage = create_stage(client, doomed_headers)
        stage_id = int(stage["id"])

        kept = {
            kind: upload_media(client, doomed_headers, "keep-{}".format(kind), kind)
            for kind in ("avatar", "prop", "backdrop")
        }
        audio_id, audio_loc = upload_media(
            client, doomed_headers, "gone-audio", "audio", filename="gone.mp3"
        )

        _, admin_headers = make_user(client, SUPER_ADMIN)
        data = gql(client, admin_headers, DELETE_USER, {"id": doomed_id})
        assert "errors" not in data, data

        session = get_session()
        admin_id = canonical_admin_id()
        assert session.query(UserModel).filter_by(id=doomed_id).first() is None
        assert session.query(StageModel).filter_by(id=stage_id).first() is None
        for asset_id, _ in kept.values():
            survivor = session.query(AssetModel).filter_by(id=asset_id).first()
            assert survivor is not None
            assert survivor.owner_id == admin_id
        assert session.query(AssetModel).filter_by(id=audio_id).first() is None
        assert not os.path.exists(os.path.join(UPLOAD_USER_CONTENT_FOLDER, audio_loc))

    async def test_04_guards(self, client):
        _, admin_headers = make_user(client, SUPER_ADMIN)

        admin_id = canonical_admin_id()
        assert admin_id is not None
        data = gql(
            client,
            admin_headers,
            DELETE_USER,
            {"id": admin_id, "contentAction": "DELETE_ALL"},
        )
        assert "errors" in data
        assert "default admin" in data["errors"][0]["message"]

        self_id, self_headers = make_user(client, SUPER_ADMIN)
        data = gql(client, self_headers, DELETE_USER, {"id": self_id})
        assert "errors" in data
        assert "your own account" in data["errors"][0]["message"]
