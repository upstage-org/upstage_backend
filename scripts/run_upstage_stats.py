from src.global_config import MQTT_BROKER, MQTT_ADMIN_PORT, MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD
from src.upstage_stats.mqtt import build_client

if __name__ == "__main__":
    print(f"Connecting to {MQTT_BROKER}:{MQTT_ADMIN_PORT} as {MQTT_ADMIN_USER}, {MQTT_ADMIN_PASSWORD}")
    client = build_client()
    print('Built client successful')
    client.username_pw_set(MQTT_ADMIN_USER, MQTT_ADMIN_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_ADMIN_PORT)
    client.loop_forever()
