import paho.mqtt.client as mqtt
import time
import random
import ssl  # Only needed if you want custom TLS options

# ================= CONFIG =================
BROKER_HOST = "testing.upstage.live"          # e.g., mqtt.example.com
BROKER_PORT = 2096
CLIENT_ID = f"python-test-client-{random.randint(1000, 9999)}"

# Authentication (from your Mosquitto config)
USERNAME = "performance"               # Set in Mosquitto password_file
PASSWORD = ""

# Topic to use for testing
TEST_TOPIC = "test/python/wss"
QOS = 1

# ================= CALLBACKS =================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✓ Connected successfully (rc={rc})")
        # Subscribe to our test topic
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

# ================= MAIN =================
client = mqtt.Client(
    client_id=CLIENT_ID,
    transport="websockets",             # Crucial: enables WSS
    protocol=mqtt.MQTTv311,              # or MQTTv5 if your Mosquitto is configured for v5
    # clean_session=True                 # Default is True
)

# Set username/password if required
client.username_pw_set(USERNAME, PASSWORD)

# Enable TLS (required for wss:// and Cloudflare/Let's Encrypt)
client.tls_set()                        # Uses system's default CA bundle (includes Let's Encrypt)

# Optional: If you get cert verification issues (rare with public Let's Encrypt):
# client.tls_set(cert_reqs=ssl.CERT_NONE)  # Insecure - only for debugging!

# Optional: Custom WebSocket path (Mosquitto usually accepts /mqtt or /)
# client.ws_set_options(path="/mqtt")   # Uncomment if needed; default is /mqtt

client.on_connect    = on_connect
client.on_disconnect = on_disconnect
client.on_message    = on_message
client.on_publish    = on_publish

print(f"Connecting to wss://{BROKER_HOST}:{BROKER_PORT} ...")

# Connect (keepalive=60 seconds is standard)
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

# Start network loop in background thread
client.loop_start()

# Publish a few test messages
try:
    for i in range(1, 6):
        message = f"Hello from Python over WSS! Message #{i} @ {time.strftime('%H:%M:%S')}"
        result = client.publish(TEST_TOPIC, message, qos=QOS)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Publish queued: {message}")
        else:
            print(f"Publish failed (rc={result.rc})")
        time.sleep(2)

    # Keep running to receive any messages (press Ctrl+C to stop)
    print("\nRunning... Press Ctrl+C to exit")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nDisconnecting...")
    client.disconnect()
    client.loop_stop()
    print("Done.")

