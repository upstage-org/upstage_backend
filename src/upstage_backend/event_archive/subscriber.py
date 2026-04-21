# -*- coding: iso8859-15 -*-
"""
MQTT subscriber task for the event_archive service.

Connects to the broker with aiomqtt, subscribes to PERFORMANCE_TOPIC_RULE, and
pushes every non-retained, non-statistics message onto an asyncio.Queue for the
writer tasks to drain. On disconnect, logs and reconnects with a backoff.
"""
import os
import sys

import asyncio
import secrets
import time

import aiomqtt

from upstage_backend.global_config import logger
from upstage_backend.global_config.env import (
    MQTT_ADMIN_PASSWORD,
    MQTT_ADMIN_PORT,
    MQTT_ADMIN_USER,
    MQTT_BROKER,
    MQTT_TRANSPORT,
    PERFORMANCE_TOPIC_RULE,
)


RECONNECT_DELAY_SECONDS = float(os.getenv("EVENT_ARCHIVE_RECONNECT_DELAY", "2.0"))
KEEPALIVE_SECONDS = int(os.getenv("EVENT_ARCHIVE_MQTT_KEEPALIVE", "30"))


def _client_id() -> str:
    return f"event_archive_{secrets.token_urlsafe(8)}"


async def subscribe_loop(queue: asyncio.Queue, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            async with aiomqtt.Client(
                hostname=MQTT_BROKER,
                port=MQTT_ADMIN_PORT,
                username=MQTT_ADMIN_USER,
                password=MQTT_ADMIN_PASSWORD,
                transport=MQTT_TRANSPORT,
                keepalive=KEEPALIVE_SECONDS,
                identifier=_client_id(),
            ) as client:
                await client.subscribe(PERFORMANCE_TOPIC_RULE)
                logger.info(
                    f"event_archive: connected to {MQTT_BROKER}:{MQTT_ADMIN_PORT}, "
                    f"subscribed to {PERFORMANCE_TOPIC_RULE}"
                )
                async for msg in client.messages:
                    if stop.is_set():
                        break
                    if getattr(msg, "retain", False):
                        continue
                    topic = msg.topic.value
                    if topic.endswith("statistics"):
                        continue
                    await queue.put(
                        {
                            "topic": topic,
                            "payload": msg.payload,
                            "ts": time.time(),
                        }
                    )
        except aiomqtt.MqttError as e:
            if stop.is_set():
                break
            logger.error(
                f"event_archive: MQTT error ({e}); reconnecting in "
                f"{RECONNECT_DELAY_SECONDS}s"
            )
            try:
                await asyncio.wait_for(stop.wait(), timeout=RECONNECT_DELAY_SECONDS)
            except asyncio.TimeoutError:
                pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("event_archive: unexpected subscriber error")
            try:
                await asyncio.wait_for(stop.wait(), timeout=RECONNECT_DELAY_SECONDS)
            except asyncio.TimeoutError:
                pass

    logger.info("event_archive: subscriber task exiting")
