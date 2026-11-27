from upstage_backend.global_config import logger

import json
import secrets

import paho.mqtt.client as mqtt
from sqlalchemy import select, update

from upstage_backend.global_config.env import MQTT_TRANSPORT
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.database import ScopedSession
from upstage_backend.upstage_stats.db_models.receive_stat import ReceiveStatModel
from upstage_backend.upstage_stats.db_models.connection_stat import ConnectionStatModel
from upstage_backend.upstage_stats.db_models.stage_statistic import StageStatisticModel


CONNECTION_TOPIC = "upstage_stats/connections"
LIVE_CLIENT_TOPIC = "upstage_stats/live_clients"
# Retained `<namespace>/<file_location>/statistics` messages carry the live
# {players, audiences} count for a stage. Subscribing here (a single connection,
# statistics-only) lets us persist those counts for the GraphQL stage-list
# resolvers, so the foyer/list no longer opens one broker WebSocket per row.
# The two-level `+/+` matches single-segment stage file locations; stage slugs
# are single segments so this stays statistics-only and never pulls in the
# high-volume board/chat topics.
STATISTICS_TOPIC_FILTER = "+/+/statistics"
client_messages = {}


def on_connect(client: mqtt.Client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(CONNECTION_TOPIC)
        connection_payload = {
            "connected": client._client_id.decode("utf-8"),
            "timestamp": utcnow().isoformat(),
            "channel": CONNECTION_TOPIC,
        }
        client.publish(CONNECTION_TOPIC, payload=json.dumps(connection_payload))

        client.subscribe(LIVE_CLIENT_TOPIC)
        client.subscribe(STATISTICS_TOPIC_FILTER)
        logger.warning("Connected successfully! Waiting for new messages...")


def record_stage_statistics(msg: mqtt.MQTTMessage):
    """Upsert a stage's latest {players, audiences} from a retained
    `<namespace>/<file_location>/statistics` message."""
    try:
        parts = msg.topic.split("/")
        if len(parts) < 3 or parts[-1] != "statistics":
            return
        stage_url = "/".join(parts[1:-1])
        payload = json.loads(msg.payload)
        players = int(payload.get("players", 0) or 0)
        audiences = int(payload.get("audiences", 0) or 0)
        with ScopedSession() as session:
            row = session.scalars(
                select(StageStatisticModel)
                .where(StageStatisticModel.stage_url == stage_url)
                .limit(1)
            ).first()
            if row:
                row.players = players
                row.audiences = audiences
                row.updated_on = utcnow()
            else:
                session.add(
                    StageStatisticModel(
                        stage_url=stage_url,
                        players=players,
                        audiences=audiences,
                        updated_on=utcnow(),
                    )
                )
    except Exception as error:
        logger.error(error)


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    global client_messages

    # Statistics messages are retained, so they must be handled before the
    # `if not msg.retain` gate below (which is for the live-client counting).
    if msg.topic.endswith("/statistics"):
        record_stage_statistics(msg)
        return

    if not msg.retain:
        client_id = client._client_id.decode("utf-8")
        # Anyone holding the shared broker login can publish here; a
        # malformed body must not take the stats worker down.
        try:
            payload = json.loads(msg.payload)
        except (ValueError, TypeError):
            logger.warning("upstage_stats: ignoring non-JSON payload on {}", msg.topic)
            return
        if not isinstance(payload, dict):
            return
        if client_id not in client_messages:
            client_messages[client_id] = 0
        if "connected" in payload:
            try:
                with ScopedSession() as session:
                    connection_stat = ConnectionStatModel(
                        connected_id=payload["connected"],
                        mqtt_timestamp=payload["timestamp"],
                        topic=payload["channel"],
                        payload=payload,
                    )
                    session.add(connection_stat)
            except Exception as error:
                logger.error(error)
        else:
            client_messages[client_id] = client_messages[client_id] + 1

        if client_messages[client_id] == 10:
            client_messages[client_id] = 0
            try:
                with ScopedSession() as session:
                    received = ReceiveStatModel.received_id == client_id
                    if not session.scalars(
                        select(ReceiveStatModel).where(received).limit(1)
                    ).first():
                        receive_stat = ReceiveStatModel(
                            received_id=client_id,
                            mqtt_timestamp=utcnow(),
                            topic=LIVE_CLIENT_TOPIC,
                            payload=payload,
                        )
                        session.add(receive_stat)
                    else:
                        session.execute(
                            update(ReceiveStatModel)
                            .where(received)
                            .values(mqtt_timestamp=utcnow(), payload=payload),
                            execution_options={"synchronize_session": False},
                        )
            except Exception as error:
                logger.error(error)


def on_disconnect(client, userdata, rc):
    client.connected_flag = False
    client.disconnect_flag = True


def get_client_id():
    return secrets.token_urlsafe(16)


def build_client(client_id=None, transport=MQTT_TRANSPORT):
    # A fresh id per client: as a default argument `get_client_id()` ran once
    # at import, so every client built by this process shared one id.
    client = mqtt.Client(client_id=client_id or get_client_id(), transport=transport)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    return client
