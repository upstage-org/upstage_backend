from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from upstage_backend.stages.db_models.stage import StageModel


class PerformanceModel(BaseModel):
    __tablename__ = "performance"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stage.id"), nullable=False, default=0, index=True
    )
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    saved_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recording: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stage: Mapped["StageModel"] = relationship("StageModel", foreign_keys=[stage_id])
