#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
srcdir = os.path.abspath(os.path.join(appdir, "../src"))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(srcdir)

from src.global_config import MQTT_BROKER, MQTT_ADMIN_PORT, MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD
from src.upstage_stats.mqtt import build_client

if __name__ == "__main__":
    client = build_client()
    client.username_pw_set(MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_ADMIN_PORT)
    client.loop_forever()
