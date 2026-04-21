# -*- coding: iso8859-15 -*-
"""
Postgres writer task for the event_archive service.

Drains items produced by the MQTT subscriber and persists each as an
EventModel row. Each event is written in its own transaction so a single
bad payload cannot poison the rest.
"""
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

import asyncio
import json

from global_config import logger
from event_archive.db.async_session import AsyncSessionLocal
from event_archive.db_models.event import EventModel


POLL_TIMEOUT_SECONDS = 1.0


class _PayloadDecodeError(Exception):
    """Raised when an MQTT payload is not a valid UTF-8 JSON value."""


def _decode_payload(raw):
    """
    Reproduce the exact shape the deleted Mongo-queue worker produced for
    EventModel.payload (postgresql.JSON): json.loads(bytes_from_wire).

    The legacy pipeline was:
        on_message : Mongo.insert_one({"payload": msg.payload})   # raw bytes
        worker     : payload = json.loads(event["payload"])        # raises on bad data
        record_event(payload=payload)                              # Python value saved as JSON

    Any payload that could not be json.loads'd never reached Postgres in the
    old code. We preserve that invariant here: if decoding fails we raise
    _PayloadDecodeError and the caller drops the event with a log entry,
    identical to the legacy worker's outer try/except behavior.
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
