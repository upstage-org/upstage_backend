#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""
Only run this manually, to load scaffolding and a demo stage.
"""
import os
import sys

import loguru 
import asyncio

from upstage_backend.stages.scripts.scaffold_base_media import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except BaseException:
        sys.exit(1)
