# -*- coding: iso8859-15 -*-

from upstage_backend.stages.db_models.parent_stage import ParentStageModel


def snapshot_exit_settings(session, stage_id=None, asset_id=None):
    """
    Capture {(stage_id, child_asset_id): (exit_animation, exit_speed)} for
    parent_stage rows about to be deleted, filtered by stage and/or asset.

    Every assignment mutation recreates its parent_stage rows from scratch,
    so callers snapshot first and rebuild via make_parent_stage() to keep
    per-assignment exit settings on the stage<->asset pairs that survive.
    """
    query = session.query(ParentStageModel)
    if stage_id is not None:
        query = query.filter(ParentStageModel.stage_id == stage_id)
    if asset_id is not None:
        query = query.filter(ParentStageModel.child_asset_id == asset_id)
    return {
        (row.stage_id, row.child_asset_id): (row.exit_animation, row.exit_speed)
        for row in query.all()
    }


def make_parent_stage(stage_id, asset_id, snapshot, exit_animation=None, exit_speed=None):
    """
    Build a parent_stage row. Each exit field independently keeps its
    explicit value when given, else falls back to the snapshot's value for
    this (stage, asset) pair — so a partial input can't wipe the other
    field. NULLs mean the default exit ("vanish" / 1000 ms, resolved
    client-side); resetting to default is done by sending those values.
    """
    stage_id = int(stage_id)
    asset_id = int(asset_id)
    snapshot_animation, snapshot_speed = snapshot.get((stage_id, asset_id), (None, None))
    return ParentStageModel(
        stage_id=stage_id,
        child_asset_id=asset_id,
        exit_animation=exit_animation if exit_animation is not None else snapshot_animation,
        exit_speed=exit_speed if exit_speed is not None else snapshot_speed,
    )
