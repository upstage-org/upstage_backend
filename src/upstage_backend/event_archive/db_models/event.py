from datetime import datetime
from typing import Any

from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel


class EventModel(BaseModel):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str | None] = mapped_column(String)
    mqtt_timestamp: Mapped[float | None] = mapped_column(Float, index=True)
    performance_id: Mapped[int | None] = mapped_column(Integer, index=True)
    payload: Mapped[Any | None] = mapped_column(postgresql.JSON)
    created: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
