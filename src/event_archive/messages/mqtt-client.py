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

import arrow
import json
from paho.mqtt import client as mqtt
import pprint
import time
import uuid

logger.add(
    "mqtt_client.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="7 days"
)

global_topic = "performance/{}"
global_domain_name = "128.199.69.170"
global_port = 1883

path_to_root_cert = str(projdir) + "/some.cert"


class MQTTClient(object):
    count_disconnects = 0

    def __init__(self, client_id, topic):
        self.domain_name = global_domain_name
        self.port = global_port
        self.client_id = client_id
        self.client = None
        self.nonzero_count = 0
        self.unacked_messages = []
        self.topic = global_topic.format(topic)

    def on_connect(self, client, userdata, flags, rc, something):
        if str(rc) == "Success":
            msg = f"Connected successfully: {rc}, Flags: {flags} {something}"
            logger.info(msg)

        else:
            msg = "Not authorized to connect, or hub time is wrong: ({0}, {1}, {2}, {3})".format(
                rc,
                pprint.pformat(client),
                pprint.pformat(userdata),
                pprint.pformat(flags),
            )
            logger.error(msg)

    def on_disconnect(self, client, userdata, rc):
        if rc == 1:
            msg = "Unexpected Connection fail: return code 1"
            logger.error(msg)
        else:
            msg = "Disconnected from the Platform"
            logger.error(msg)

        self.count_disconnects += 1
        if self.count_disconnects > 10:
            msg = "Process unexpectedly disconnected more than 10 times, killing and restarting the process."
            logger.error(msg)
            sys.exit(-1)

    def on_message(self, client, userdata, msg):
        msg = " - ".join((msg.topic, str(msg.payload)))
        logger.warning(msg)

    def on_publish(self, client, userdata, mid):
        msg = "Publish Callback message ID for internal: {0}".format(mid)
        logger.warning(msg)
        self.count_disconnects = 0
        if mid in self.unacked_messages:
            self.unacked_messages.remove(mid)

    def on_log(self, client, userdata, level, buffer):
        msg = "Log entry from device {0}: {1}, {2}, {3}".format(
            self.client_id, level, buffer, userdata
        )
        logger.warning(msg)

    def client_start(self, on_message=None):
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv5)
        self.client.username_pw_set(
            username="performance", password="z48FCTsJVEUkYmtUw5S9"
        )
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message if not on_message else on_message
        self.client.on_publish = self.on_publish
        self.client.on_log = self.on_log
        """
        self.client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
        self.client.tls_insecure_set(False)
        """

        self.client.connect(self.domain_name, port=self.port)
        logger.warning("Connected")
        self.client.loop_start()

    def client_publish(self, json_payload):
        result, message_id = self.client.publish(
            self.topic, payload=json_payload, qos=1, retain=False
        )
        if result != 0:
            msg = "Published message ID {0}: return code is not zero: {1}".format(
                message_id, result
            )
            logger.error(msg)
            self.nonzero_count += 1
            if self.nonzero_count >= 10:
                msg = "Process for device {0} had greater than 10 publish failures, killing and restarting the process.".format(
                    self.client_id
                )
                logger.error(msg)
                sys.exit(-1)
        else:
            msg = "Published message ID {0}: {1}".format(message_id, result)
            logger.warning(msg)
            self.unacked_messages.append(message_id)

    def client_shutdown(self):
        self.client.loop_stop()
        self.client.disconnect()


if __name__ == "__main__":
    # Each client id has to be unique, so the origin can be identified.
    # client_id = configdata['gid'][8:].upper() + '_' + str(int(arrow.utcnow().timestamp))
    client_id = str(uuid.uuid4())
    topic = "performance_topic_name"

    if sys.argv[1] == "publish":
        x = MQTTClient(client_id, topic)
        x.client_start()
        count = 0
        try:
            while True:
                count += 1
                outbound = {
                    "timestamp": f"{arrow.utcnow().timestamp}",
                    "count": f"{count}",
                }
                x.client_publish(json.dumps(outbound))
                time.sleep(5)
                logger.warning("Publishing: {0}".format(count))
        finally:
            x.client_shutdown()

    elif sys.argv[1] == "subscribe":
        x = MQTTClient(client_id, topic)
        x.client_start()
        try:
            # Subscribe to a device other than your own
            x.client.subscribe(x.topic)
            while True:
                time.sleep(5)
        finally:
            x.client_shutdown()
