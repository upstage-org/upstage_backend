#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)

from src.global_config import MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD, MQTT_BROKER, MQTT_ADMIN_PORT
from src.event_archive.systems.system import run
from src.event_archive.messages.mqtt import build_client

if __name__ == "__main__":
    run()
    mqtt_client = build_client()
    mqtt_client.username_pw_set(MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD)
    mqtt_client.connect(MQTT_BROKER, MQTT_ADMIN_PORT)
    mqtt_client.loop_forever()
