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


def sync_asset_assignments(session, asset_id, wanted):
    """
    Make one media item's stage assignments equal ``wanted`` — an iterable of
    ``(stage_id, exit_animation, exit_speed)`` — touching as few rows as
    possible.

    A stage's saved media order IS the parent_stage primary-key order
    (assignMedia writes the rows in the order arranged in Stage Management >
    Media; StageModel.assets reads them back ORDER BY id). The per-media
    mutations used to delete all of the item's rows and insert fresh ones, so
    simply re-saving a media item gave it new, higher ids and silently moved
    it to the END of the order on every stage it was already on. Here an
    assignment that survives keeps its row, and therefore its position; only
    a genuinely new assignment is inserted (at the end, as before), and only
    a dropped one is deleted.

    Exit settings follow the make_parent_stage() rule: an explicit value
    wins, ``None`` keeps what the pair already had.

    parent_stage has no unique constraint, so racing saves can leave the same
    (stage, asset) pair twice; the earliest row (the saved position) is kept
    and the extras are removed. A stage id repeated in ``wanted`` is used once.

    Changes are left pending in ``session`` for the caller to flush.
    """
    asset_id = int(asset_id)
    existing = {}
    for row in (
        session.query(ParentStageModel)
        .filter(ParentStageModel.child_asset_id == asset_id)
        .order_by(ParentStageModel.id)
        .all()
    ):
        if row.stage_id in existing:
            session.delete(row)
        else:
            existing[row.stage_id] = row

    seen = set()
    for stage_id, exit_animation, exit_speed in wanted:
        stage_id = int(stage_id)
        if stage_id in seen:
            continue
        seen.add(stage_id)
        row = existing.get(stage_id)
        if row is None:
            session.add(
                ParentStageModel(
                    stage_id=stage_id,
                    child_asset_id=asset_id,
                    exit_animation=exit_animation,
                    exit_speed=exit_speed,
                )
            )
            continue
        if exit_animation is not None:
            row.exit_animation = exit_animation
        if exit_speed is not None:
            row.exit_speed = exit_speed

    for stage_id, row in existing.items():
        if stage_id not in seen:
            session.delete(row)
