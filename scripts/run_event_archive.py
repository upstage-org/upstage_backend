#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""
Entry point for the event_archive service.

Hands control to src.event_archive.main.main(), which runs a single
asyncio.TaskGroup containing the MQTT subscriber and N Postgres writers.
Non-zero exit on any task failure so Docker restarts the container.

Runs from any CWD, with or without PYTHONPATH set: this script resolves
its own location via __file__ and puts the project root and src/ on
sys.path before any project imports.
"""
import os
import sys

import asyncio

from upstage_backend.event_archive.main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except BaseException:
        sys.exit(1)
