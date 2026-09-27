from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.users.db_models.user import UserModel


class PerformanceMQTTConfigModel(BaseModel):
    # This holds the MQTT server configuration for one performance, to make connecting easier.
    # There may be > 1 MQTT connection in a performance.
    __tablename__ = "live_performance_mqtt_config"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    ip_address: Mapped[str] = mapped_column(Text, nullable=False)
    websocket_port: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    webclient_port: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """
    Performance connections will be namespaced by a unique string, so a user can be
    connected to more than one stage at once.
    The topic_name should be modified when this expires, so it can be reused
    in the future. MQTT will send /performance/topic_name as the leading topic.
    """
    topic_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=None
    )
    performance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("performance_config.id"), nullable=False, default=0, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upstage_user.id"), nullable=False, default=0
    )

    owner: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[owner_id])
    # performance_config = relationship(
    #     "PerformanceConfigModel", foreign_keys=[performance_id]
    # )
