#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
"""
Entry point for the event_archive service.

Hands control to ``upstage_backend.event_archive.main.main()``, which runs
a single ``asyncio.TaskGroup`` containing the MQTT subscriber and N
Postgres writers. Non-zero exit on any task failure so Docker restarts
the container.

Imports work from any CWD because ``upstage_backend`` is editable-
installed (``pip install -e .``) into the venv at container build time
(see ``app_containers/docker-compose.yaml`` ``x-common-build`` runtime
stage). No ``sys.path`` manipulation, no ``PYTHONPATH`` exports.
"""

import sys

import loguru  # noqa: F401  # entrypoint: load loguru before upstage (see app_containers compose)
import asyncio

from upstage_backend.event_archive.main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except BaseException:
        sys.exit(1)
