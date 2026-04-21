# -*- coding: iso8859-15 -*-
"""
Async entry point for the event_archive service.

Wires one MQTT subscriber, N Postgres writers, and a supervisor heartbeat
inside an asyncio.TaskGroup. Any unhandled exception in any child task
cancels its siblings, an ExceptionGroup bubbles up to the process exit code,
and the container is restarted by Docker.
"""
import os
import sys

import asyncio
import signal

from upstage_backend.global_config import logger
from upstage_backend.event_archive.db.async_session import async_engine
from upstage_backend.event_archive.subscriber import subscribe_loop
from upstage_backend.event_archive.writer import writer_loop


QUEUE_CAPACITY = int(os.getenv("EVENT_ARCHIVE_QUEUE_CAPACITY", "10000"))
WRITER_CONCURRENCY = int(os.getenv("EVENT_ARCHIVE_WRITERS", "4"))
HEARTBEAT_SECONDS = float(os.getenv("EVENT_ARCHIVE_HEARTBEAT_SECONDS", "30"))


async def _supervisor(queue: asyncio.Queue, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
        except asyncio.TimeoutError:
            logger.info(
                f"event_archive: heartbeat queue_depth={queue.qsize()}/"
                f"{QUEUE_CAPACITY}"
            )


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows / restricted envs: fall back to default handling.
            pass


async def main() -> None:
    queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_CAPACITY)
    stop = asyncio.Event()
    _install_signal_handlers(stop)

    logger.info(
        f"event_archive: starting (writers={WRITER_CONCURRENCY}, "
        f"queue_capacity={QUEUE_CAPACITY})"
    )

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(subscribe_loop(queue, stop), name="mqtt-subscriber")
            for i in range(WRITER_CONCURRENCY):
                tg.create_task(writer_loop(i, queue, stop), name=f"pg-writer-{i}")
            tg.create_task(_supervisor(queue, stop), name="supervisor")

            await stop.wait()
            try:
                await asyncio.wait_for(queue.join(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(
                    f"event_archive: queue did not drain within 10s "
                    f"({queue.qsize()} items remaining)"
                )
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.exception(f"event_archive: task failed: {exc!r}")
        raise
    finally:
        await async_engine.dispose()
        logger.info("event_archive: shutdown complete")
