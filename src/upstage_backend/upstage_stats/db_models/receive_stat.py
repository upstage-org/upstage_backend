from typing import Any
from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel
from sqlalchemy.dialects import postgresql


class ReceiveStatModel(BaseModel):
    __tablename__ = "receive_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    received_id: Mapped[str | None] = mapped_column(String, index=True)
    mqtt_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    topic: Mapped[str | None] = mapped_column(String)
    payload: Mapped[Any | None] = mapped_column(postgresql.JSON)
    created: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
