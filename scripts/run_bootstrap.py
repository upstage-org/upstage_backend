#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""
One-shot install bootstrap, chained after alembic in the upstage_db_migrate
container: seeds the Demo Stage ONLY when the stage table is empty (a new
installation), so every deployment has a default stage that new players are
automatically added to.

Exit codes: 0 when seeding succeeded OR was skipped (stages already exist —
the normal case on every established install); non-zero when a fresh install
failed to seed, which blocks the dependent services on purpose: the scaffold's
transaction has been rolled back, so a re-`up` retries cleanly.

Pass --force to seed even when stages exist (controlled re-seeding in dev;
each scaffold step is idempotent and only tops up what is missing).

For the legacy manual, ungated path see run_scaffold_load.py.
"""

import sys

from upstage_backend.stages.scripts.bootstrap import bootstrap

if __name__ == "__main__":
    try:
        bootstrap(force="--force" in sys.argv)
    except KeyboardInterrupt:
        sys.exit(0)
