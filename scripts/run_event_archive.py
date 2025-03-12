#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, "../src"))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)

from global_config import MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD, MQTT_BROKER, MQTT_ADMIN_PORT
from src.event_archive.systems.system import run
from src.event_archive.messages.mqtt import build_client

if __name__ == "__main__":
    print(f"Connecting to {MQTT_BROKER}:{MQTT_ADMIN_PORT} as {MQTT_ADMIN_USER}, {MQTT_ADMIN_PASSWORD}")
    run()
    print('Running event archive')
    mqtt_client = build_client()
    print('Built client successful')
    mqtt_client.username_pw_set(MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD)
    mqtt_client.connect(MQTT_BROKER, MQTT_ADMIN_PORT)
    mqtt_client.loop_forever()
