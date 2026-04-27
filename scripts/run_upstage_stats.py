#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
import os
import sys

#import loguru  # noqa: F401  # entrypoint: load loguru before upstage (see app_containers compose)

from upstage_backend.global_config import MQTT_BROKER, MQTT_ADMIN_PORT, MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD
from upstage_backend.upstage_stats.mqtt import build_client

if __name__ == "__main__":
    client = build_client()
    client.username_pw_set(MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_ADMIN_PORT)
    client.loop_forever()
