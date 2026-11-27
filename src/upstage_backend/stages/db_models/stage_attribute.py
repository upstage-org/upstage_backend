from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.stages.db_models.stage import StageModel


class StageAttributeModel(BaseModel):
    __tablename__ = "stage_attribute"
    # Attributes are always read per stage by name (StageService / permissions).
    __table_args__ = (Index("ix_stage_attribute_stage_id_name", "stage_id", "name"),)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stage.id"), nullable=False, default=0
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    stage: Mapped["StageModel"] = relationship(
        "StageModel", foreign_keys=[stage_id], back_populates="attributes"
    )
