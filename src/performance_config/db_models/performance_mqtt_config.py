from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Text
from global_config import BaseModel


class PerformanceMQTTConfigModel(BaseModel):
    # This holds the MQTT server configuration for one performance, to make connecting easier.
    # There may be > 1 MQTT connection in a performance.
    __tablename__ = "live_performance_mqtt_config"
    id = Column(BigInteger, primary_key=True)
    ip_address = Column(Text, nullable=False)
    websocket_port = Column(Integer, nullable=False, default=0)
    webclient_port = Column(Integer, nullable=False, default=0)
    """
    Performance connections will be namespaced by a unique string, so a user can be
    connected to more than one stage at once.
    The topic_name should be modified when this expires, so it can be reused
    in the future. MQTT will send /performance/topic_name as the leading topic.
    """
    topic_name = Column(Text, unique=True, nullable=False)
    username = Column(Text, nullable=False)
    password = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    expires_on = Column(DateTime, nullable=False, default=None)
    performance_id = Column(
        Integer, ForeignKey("performance_config.id"), nullable=False, default=0
    )
    owner_id = Column(Integer, ForeignKey("upstage_user.id"), nullable=False, default=0)

    owner = relationship("UserModel", foreign_keys=[owner_id])
    # performance_config = relationship(
    #     "PerformanceConfigModel", foreign_keys=[performance_id]
    # )
