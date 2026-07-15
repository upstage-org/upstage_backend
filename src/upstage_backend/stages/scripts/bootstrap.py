# -*- coding: iso8859-15 -*-
"""New-installation bootstrap: seed the Demo Stage when the database has no
stages at all (the "fresh install" signal). Invoked by scripts/run_bootstrap
inside the one-shot upstage_db_migrate container, right after alembic reaches
heads — so every new deployment gets a default stage for new players (the
assign_user_to_default_stage hook adds them to it by its exact name).
"""

from upstage_backend.global_config import logger
from upstage_backend.global_config.database import ScopedSession
from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.stages.scripts import scaffold_base_media


def is_new_installation(session) -> bool:
    return session.query(StageModel).count() == 0


def bootstrap(force: bool = False) -> bool:
    """Seed the demo scaffold on a new installation. Returns True when the
    scaffold ran, False when it was skipped because stages already exist.
    `force` bypasses the gate (used for controlled re-seeding in dev)."""
    with ScopedSession() as session:
        new_installation = is_new_installation(session)
    if not new_installation and not force:
        logger.warning("⏩ Stages already exist; skipping the demo-stage scaffold.")
        return False
    scaffold_base_media.main()
    return True
