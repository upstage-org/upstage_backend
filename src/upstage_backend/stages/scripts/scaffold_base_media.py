# -*- coding: iso8859-15 -*-
"""Seed a new installation with the Demo Stage.

Manifest-driven: everything comes from dashboard/demo/seed/demo_stage_seed.json
(a sanitized capture of the live upstage.live Demo Stage) plus the media files
shipped alongside it under dashboard/demo/, which are copied into the uploads
volume with their original hashed names — the scene payload and the seeded
board events reference those names via /resources/... URLs.

The stage MUST be named exactly "Demo Stage": StageOperationService.
assign_user_to_default_stage looks it up by that name to grant every newly
created user player access, and silently no-ops otherwise.

Run paths:
  - Automatically on new installations (zero stages) via scripts/run_bootstrap
    inside the one-shot upstage_db_migrate container, after alembic.
  - Manually (ungated) via scripts/run_scaffold_load.

Every step is idempotent, so a manual re-run tops up whatever is missing
(assets dedupe by file_location; the stage, scene and board events are
skipped when they already exist).
"""

import os

from upstage_backend.global_config import logger

import json
import shutil
import time

from upstage_backend.assets.db_models.asset_type import AssetTypeModel
from upstage_backend.assets.db_models.asset import AssetModel

# AssetModel declares string-name relationships to AssetLicenseModel and
# MediaTagModel. SQLAlchemy resolves those strings the first time the mapper
# configures (i.e. the first session.query(...) call below), and resolution
# fails unless both classes have been imported so they are present in
# Base.registry. The web process picks them up transitively via HTTP/service
# modules, but this standalone scaffold does not.
#
# As of the asset db_models package __init__.py re-exports, simply importing
# AssetModel above is already enough to register all sibling asset models.
# The explicit imports here are defensive: they pin the dependency at the call
# site so a future refactor of the package __init__.py cannot silently
# resurrect this bug.
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel  # noqa: F401
from upstage_backend.assets.db_models.media_tag import MediaTagModel  # noqa: F401
from upstage_backend.event_archive.db_models.event import EventModel
from upstage_backend.performance_config.db_models.scene import SceneModel
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel
from upstage_backend.stages.db_models.parent_stage import ParentStageModel
from upstage_backend.stages.services.stage import StageService
from upstage_backend.users.db_models.user import UserModel, ADMIN, GUEST
from upstage_backend.upstage_options.db_models.config import ConfigModel
from upstage_backend.global_config.helpers.fernet_crypto import encrypt
from upstage_backend.global_config.env import (
    UPLOAD_USER_CONTENT_FOLDER,
    DEMO_MEDIA_FOLDER,
)
from upstage_backend.global_config.database import ScopedSession

SEED_FILE = os.path.join("seed", "demo_stage_seed.json")


def load_seed():
    with open(os.path.join(DEMO_MEDIA_FOLDER, SEED_FILE)) as f:
        return json.load(f)


def copy_file(rel_path):
    """Copy one shipped demo file into the uploads volume, preserving its
    upload-relative path (and hashed name). Idempotent overwrite."""
    src = os.path.join(DEMO_MEDIA_FOLDER, rel_path)
    dest = os.path.join(UPLOAD_USER_CONTENT_FOLDER, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    return os.path.getsize(src)


def get_or_create_asset_type(session, name):
    asset_type = session.query(AssetTypeModel).filter(AssetTypeModel.name == name).first()
    if not asset_type:
        asset_type = AssetTypeModel(name=name, file_location="")
        session.add(asset_type)
        session.flush()
    return asset_type


def create_asset(session, owner_id, spec):
    """Create (or reuse) one manifest asset. Files are always (re)copied so
    the uploads volume is complete even when the row already existed."""
    size = copy_file(spec["file_location"])
    for extra in spec.get("extra_files", []):
        size += copy_file(extra)

    # Dedupe by file_location alone: a re-run (or a re-seed after the demo
    # stage was deleted) must reuse the original asset rows so archived
    # performances keep pointing at valid assets.
    asset = (
        session.query(AssetModel).filter(AssetModel.file_location == spec["file_location"]).first()
    )
    if asset:
        logger.warning(
            '⏩ Reusing existing demo {} "{}" (asset id={})'.format(
                spec["type"], spec["name"], asset.id
            )
        )
        return asset

    asset = AssetModel(
        name=spec["name"],
        asset_type=get_or_create_asset_type(session, spec["type"]),
        owner_id=owner_id,
        file_location=spec["file_location"],
        description=json.dumps(spec["description"]),
        size=size,
    )
    session.add(asset)
    session.flush()
    logger.warning('✅ Created {} "{}"'.format(spec["type"], spec["name"]))
    return asset


def create_demo_media(session, owner_id, seed):
    """Create the predetermined media set: the stage-assigned assets plus the
    default media that ships loaded-but-unassigned (e.g. the Chart backdrop
    the Demo scene's background uses).

    Returns [(asset_id, exit_animation, exit_speed), ...] for stage assignment.
    """
    media = []
    for spec in seed["assets"]:
        asset = create_asset(session, owner_id, spec)
        media.append((asset.id, spec.get("exit_animation"), spec.get("exit_speed")))
    for spec in seed.get("unassigned_assets", []):
        create_asset(session, owner_id, spec)
    return media


def create_demo_stage(session, owner_id, media, seed):
    """Create the Demo Stage with its attributes and media assignments.
    Returns the stage (existing or new); when it already exists nothing is
    touched — the scene/event seeders below have their own skip guards."""
    spec = seed["stage"]
    existing = (
        session.query(StageModel)
        .filter(
            (StageModel.name == spec["name"]) | (StageModel.file_location == spec["file_location"])
        )
        .first()
    )
    if existing:
        logger.warning(
            '⏩ Stage "{}" (file_location="{}") already exists; not recreating.'.format(
                existing.name, existing.file_location
            )
        )
        return existing

    # file_location is the live/MQ topic namespace (see StageService /
    # sweep_stage); it must be unique. The seed asks for "demo" — fall back to
    # a generated slug only if something else already claimed it (possible
    # because the name check above matches on EITHER name or slug).
    file_location = spec["file_location"]
    if session.query(StageModel).filter(StageModel.file_location == file_location).first():
        file_location = StageService().get_short_name(spec["name"], session)

    stage = StageModel(
        name=spec["name"],
        owner_id=owner_id,
        description=spec["description"],
        file_location=file_location,
    )
    # StageService.create/update also mirrors description into an attribute
    # row; seed the same shape so a later Save doesn't change anything.
    attributes = dict(spec["attributes"])
    attributes["description"] = spec["description"]
    for name, value in attributes.items():
        stage.attributes.append(StageAttributeModel(name=name, description=value))

    session.add(stage)
    session.flush()
    for asset_id, exit_animation, exit_speed in media:
        session.add(
            ParentStageModel(
                stage_id=stage.id,
                child_asset_id=asset_id,
                exit_animation=exit_animation,
                exit_speed=exit_speed,
            )
        )
    session.flush()
    logger.warning(
        '✅ Created demo stage "{}" (file_location="{}" for live topics)'.format(
            stage.name, file_location
        )
    )
    return stage


def create_demo_scene(session, stage, owner_id, seed):
    if session.query(SceneModel).filter(SceneModel.stage_id == stage.id).first():
        logger.warning("⏩ Stage already has scenes; not seeding the demo scene.")
        return
    spec = seed["scene"]
    session.add(
        SceneModel(
            name=spec["name"],
            scene_order=spec.get("scene_order", 1),
            scene_preview=spec.get("scene_preview"),
            payload=json.dumps(spec["payload"]),
            active=spec.get("active", True),
            owner_id=owner_id,
            stage_id=stage.id,
        )
    )
    session.flush()
    logger.warning('✅ Created demo scene "{}"'.format(spec["name"]))


def seed_board_events(session, stage, seed):
    """Put the initial objects on the board. Board state is materialised by
    replaying live events (get_event_list matches topic %/<slug>/% with any
    prefix), so plain event rows with a fixed prefix work on any install."""
    existing = (
        session.query(EventModel)
        .filter(
            EventModel.performance_id == None,  # noqa: E711  (SQLAlchemy column NULL comparison)
            EventModel.topic.like("%/{}/%".format(stage.file_location)),
        )
        .first()
    )
    if existing:
        logger.warning("⏩ Stage already has live events; not seeding the board.")
        return
    timestamp = time.time()
    for offset, event in enumerate(seed["board_events"]):
        session.add(
            EventModel(
                topic="upstage/{}/{}".format(stage.file_location, event["topic_suffix"]),
                # Tiny increasing offsets keep replay order deterministic.
                mqtt_timestamp=timestamp + offset * 0.001,
                performance_id=None,
                payload=event["payload"],
            )
        )
    session.flush()
    logger.warning(
        "✅ Seeded {} board object(s) onto the demo stage".format(len(seed["board_events"]))
    )


DEFAULT_SCAFFOLD_PASSWORD = "12345678"


def get_or_create_user(session, username, email, role, password=None):
    existing = (
        session.query(UserModel)
        .filter((UserModel.username == username) | (UserModel.email == email))
        .first()
    )
    if existing:
        logger.warning('⏩ A user "{}" / "{}" already exists.'.format(username, email))
        return existing

    password = password or DEFAULT_SCAFFOLD_PASSWORD
    user = UserModel()
    user.username = username
    user.password = encrypt(password)
    user.email = email
    user.role = role
    user.active = True
    session.add(user)
    session.flush()
    logger.warning(
        '✅ Created account with credentials: "{}" and password "{}"'.format(username, password)
    )
    return user


def create_demo_users(session):
    """Create the default logins: admin, guest, and the Demo1 player used in
    demos/workshops (its password is the one publicly documented in the
    upstage.live foyer text). Returns the Demo1 user so it can be granted
    player access on the Demo Stage."""
    get_or_create_user(session, "admin", "support@upstage.live", ADMIN)
    get_or_create_user(session, "guest", "guest@upstage.live", GUEST)
    return get_or_create_user(
        session, "Demo1", "demo1@upstage.org.nz", GUEST, password="DemoUpStage"
    )


def grant_player_access(session, stage, users):
    """Append the given users to the stage's playerAccess player list
    (index 0 — same contract as assign_user_to_default_stage, inlined here
    because the scaffold owns its own session). Idempotent."""
    attribute = stage.attributes.filter(StageAttributeModel.name == "playerAccess").first()
    if not attribute or not attribute.description:
        return
    try:
        accesses = json.loads(attribute.description)
    except (TypeError, json.JSONDecodeError):
        return
    if not isinstance(accesses, list) or not accesses or not isinstance(accesses[0], list):
        return
    changed = False
    for user in users:
        user_id = str(user.id)
        if user_id not in accesses[0]:
            accesses[0].append(user_id)
            changed = True
    if changed:
        attribute.description = json.dumps(accesses)
        session.flush()
        logger.warning(
            '✅ Granted player access on "{}" to: {}'.format(
                stage.name, ", ".join(u.username for u in users)
            )
        )


def save_config(session, name, value):
    """Fill in a default ONLY when the key is missing. Existing values are
    operator configuration (foyer text, T&Cs, ...) that a re-run — manual or
    --force — must never clobber."""
    config = session.query(ConfigModel).filter(ConfigModel.name == name).first()
    if config:
        logger.warning('⏩ Config "{}" already set; keeping existing value.'.format(name))
        return
    session.add(ConfigModel(name=name, value=value))
    session.flush()


def scaffold_foyer(session):
    save_config(session, "FOYER_TITLE", "Your New UpStage")
    save_config(
        session,
        "FOYER_DESCRIPTION",
        "Welcome to your new UpStage! Log in to get started.",
    )
    logger.warning("✅ Foyer Scaffolding Completed")


def scaffold_system_configuration(session):
    # Match Alembic default (e5f8bc8043a5): user-facing T&Cs, not repo LICENSE.
    save_config(
        session,
        "TERMS_OF_SERVICE",
        "https://upstage.org.nz/?page_id=9622",
    )
    save_config(session, "MANUAL", "https://docs.upstage.live")
    logger.warning("✅ System Configuration Scaffolding Completed")


def main():
    seed = load_seed()
    with ScopedSession() as s:
        # Users first, so the admin lookup below finds the account this very
        # run created on a fresh database.
        demo_player = create_demo_users(s)
        owner = s.query(UserModel).filter(UserModel.username == "admin").first()
        owner_id = owner.id if owner else 0

        media = create_demo_media(s, owner_id, seed)
        stage = create_demo_stage(s, owner_id, media, seed)
        create_demo_scene(s, stage, owner_id, seed)
        seed_board_events(s, stage, seed)
        # Users created via the API get this from assign_user_to_default_stage;
        # scaffold-created logins need it granted here.
        grant_player_access(s, stage, [demo_player])
        scaffold_foyer(s)
        scaffold_system_configuration(s)


if __name__ == "__main__":
    main()
