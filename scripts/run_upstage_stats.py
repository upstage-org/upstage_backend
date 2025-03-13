#!/usr/bin/env python
# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)

from global_config import MQTT_BROKER, MQTT_ADMIN_PORT, MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD
from src.upstage_stats.mqtt import build_client

if __name__ == "__main__":
    print(f"Connecting to {MQTT_BROKER}:{MQTT_ADMIN_PORT} as {MQTT_ADMIN_USER}, {MQTT_ADMIN_PASSWORD}")
    client = build_client()
    print('Built client successful')
    client.username_pw_set(MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_ADMIN_PORT)
    client.loop_forever()
