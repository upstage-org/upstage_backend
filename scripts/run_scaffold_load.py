#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""
Only run this manually, to load scaffolding and a demo stage.
"""

import sys

from upstage_backend.stages.scripts.scaffold_base_media import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
