# -*- coding: iso8859-15 -*-
import os
import sys

from src.global_config import logger

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

import secrets
from time import time

import paho.mqtt.client as paho

from global_config.env import (
    EVENT_COLLECTION,
    MONGO_DB,
    MQTT_TRANSPORT,
    PERFORMANCE_TOPIC_RULE,
)
from event_archive.config.mongodb import build_mongo_client


def on_connect(client, userdata, flags, rc):
    client.subscribe(PERFORMANCE_TOPIC_RULE)
    logger.info("Connected successfully! Waiting for new messages...")


def on_message(client, userdata, msg: paho.MQTTMessage):
    if not msg.retain:
        try:
            client = build_mongo_client()
            db = client[MONGO_DB]
            db[EVENT_COLLECTION].insert_one(
                {"topic": msg.topic, "payload": msg.payload, "timestamp": time()}
            )
            client.close()
        except Exception as e:
            logger.error(e)


def get_client_id():
    return secrets.token_urlsafe(16)


def build_client(client_id=get_client_id(), transport=MQTT_TRANSPORT):
    client = paho.Client(client_id=client_id, transport=transport)
    client.on_connect = on_connect
    client.on_message = on_message
    return client
