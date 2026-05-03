# -*- coding: iso8859-15 -*-
"""
Postgres writer task for the event_archive service.

Drains items produced by the MQTT subscriber and persists each as an
EventModel row. Each event is written in its own transaction so a single
bad payload cannot poison the rest.
"""
import os
import sys

import asyncio
import json

from upstage_backend.global_config import logger
from upstage_backend.event_archive.db.async_session import AsyncSessionLocal
from upstage_backend.event_archive.db_models.event import EventModel


POLL_TIMEOUT_SECONDS = 1.0


class _PayloadDecodeError(Exception):
    """Raised when an MQTT payload is not a valid UTF-8 JSON value."""


def _decode_payload(raw):
    """
    Decode MQTT payload bytes/str to a Python value for EventModel.payload
    (postgresql.JSON), matching the legacy pipeline: raw bytes on the wire,
    ``json.loads`` before insert.

    Any payload that could not be decoded is dropped by the caller with a log
    line, same as the old archive worker.
    """
    if isinstance(raw, (bytes, bytearray)):
        try:
            return json.loads(bytes(raw))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise _PayloadDecodeError(str(e)) from e
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise _PayloadDecodeError(str(e)) from e
    raise _PayloadDecodeError(f"unsupported payload type: {type(raw).__name__}")


async def writer_loop(
    worker_id: int, queue: asyncio.Queue, stop: asyncio.Event
) -> None:
    logger.info(f"event_archive: writer {worker_id} started")
    try:
        while not (stop.is_set() and queue.empty()):
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=POLL_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                continue

            topic = item.get("topic", "")
            ts = item.get("ts")
            raw_payload = item.get("payload")

            try:
                payload = _decode_payload(raw_payload)
            except _PayloadDecodeError as e:
                logger.error(
                    f"event_archive: writer {worker_id} dropping event "
                    f"topic={topic!r} ts={ts}: invalid payload ({e})"
                )
                queue.task_done()
                continue

            try:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        session.add(
                            EventModel(
                                topic=topic,
                                payload=payload,
                                mqtt_timestamp=ts,
                                performance_id=None,
                            )
                        )
            except Exception:
                logger.exception(
                    f"event_archive: writer {worker_id} failed to persist "
                    f"topic={topic!r} ts={ts}"
                )
            finally:
                queue.task_done()
    except asyncio.CancelledError:
        raise
    finally:
        logger.info(f"event_archive: writer {worker_id} exiting")
