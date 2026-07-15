#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""
Only run this manually, to load scaffolding and a demo stage — no gate, it
always runs (each step is idempotent). The docker install path is
run_bootstrap.py, which seeds only when the database has zero stages.
"""

import sys

from upstage_backend.stages.scripts.scaffold_base_media import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
