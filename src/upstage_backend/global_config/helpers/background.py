"""
Fire-and-forget coroutine launcher that keeps a strong reference to the task.

``asyncio.create_task`` only holds a weak reference; a task nobody references
can be garbage-collected mid-flight and its exception is silently lost
(Python docs, "Important" note under create_task). Every background send in
the services goes through ``spawn`` so the task survives until it finishes
and failures land in the log.
"""

import asyncio
from typing import Coroutine, Set

from upstage_backend.global_config.logger import logger

_TASKS: Set["asyncio.Task"] = set()


def _reap(task: "asyncio.Task") -> None:
    _TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.opt(exception=exc).error("background task failed: {}", task.get_name())


def spawn(coro: Coroutine, name: str | None = None) -> "asyncio.Task":
    task = asyncio.create_task(coro, name=name)
    _TASKS.add(task)
    task.add_done_callback(_reap)
    return task
