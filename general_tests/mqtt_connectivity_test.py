"""
Manual MQTT-over-WSS smoke test against a remote broker.

This file is intentionally NOT a pytest module — there are no test_* functions
and the broker call is gated behind `if __name__ == "__main__":`. The previous
shape ran `client.connect(...)` at import time, which blocked
`pytest --collect-only` (and any other tool that imports the file) on a real
network round-trip to testing.upstage.live:2096.

Run as:
    python general_tests/mqtt_connectivity_test.py

Press Ctrl+C to stop. To target a different broker, edit the CONFIG block
below or wrap this script in your own runner.
"""

import paho.mqtt.client as mqtt
import time
import random
import ssl  # Only needed if you want custom TLS options


# ================= CONFIG =================
BROKER_HOST = "testing.upstage.live"  # e.g., mqtt.example.com
BROKER_PORT = 2096
CLIENT_ID = f"python-test-client-{random.randint(1000, 9999)}"

# Authentication (from your Mosquitto config)
USERNAME = "performance"  # Set in Mosquitto password_file
PASSWORD = ""

# Topic to use for testing
TEST_TOPIC = "test/python/wss"
QOS = 1


# ================= CALLBACKS =================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✓ Connected successfully (rc={rc})")
        client.subscribe(TEST_TOPIC, qos=QOS)
        print(f"Subscribed to {TEST_TOPIC}")
    else:
        print(f"Connection failed with code {rc}")


def on_disconnect(client, userdata, rc, properties=None):
    print(f"Disconnected (rc={rc})")


def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()} (QoS={msg.qos})")


def on_publish(client, userdata, mid, properties=None):
    print(f"Message published (mid={mid})")


def main() -> None:
    """Connect to the configured broker, publish 5 test messages, then idle."""
    client = mqtt.Client(
        client_id=CLIENT_ID,
        transport="websockets",  # Crucial: enables WSS
        protocol=mqtt.MQTTv311,  # or MQTTv5 if your Mosquitto is configured for v5
    )

    client.username_pw_set(USERNAME, PASSWORD)

    # Enable TLS (required for wss:// and Cloudflare/Let's Encrypt). Uses the
    # system's default CA bundle, which already trusts Let's Encrypt roots.
    client.tls_set()

    # Optional: bypass cert verification for debugging. Insecure — leave off
    # in normal use:
    #   client.tls_set(cert_reqs=ssl.CERT_NONE)
    _ = ssl  # keep ssl imported for the commented-out debug knob above

    # Optional: custom WebSocket path (Mosquitto usually accepts /mqtt or /):
    #   client.ws_set_options(path="/mqtt")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_publish = on_publish

    print(f"Connecting to wss://{BROKER_HOST}:{BROKER_PORT} ...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    try:
        for i in range(1, 6):
            message = (
                f"Hello from Python over WSS! Message #{i} "
                f"@ {time.strftime('%H:%M:%S')}"
            )
            result = client.publish(TEST_TOPIC, message, qos=QOS)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Publish queued: {message}")
            else:
                print(f"Publish failed (rc={result.rc})")
            time.sleep(2)

        print("\nRunning... Press Ctrl+C to exit")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nDisconnecting...")
        client.disconnect()
        client.loop_stop()
        print("Done.")


if __name__ == "__main__":
    main()
