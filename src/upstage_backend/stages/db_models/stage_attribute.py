from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from upstage_backend.global_config.db_models.base import BaseModel


class StageAttributeModel(BaseModel):
    __tablename__ = "stage_attribute"
    # Attributes are always read per stage by name (StageService / permissions).
    __table_args__ = (Index("ix_stage_attribute_stage_id_name", "stage_id", "name"),)
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    stage_id = Column(Integer, ForeignKey("stage.id"), nullable=False, default=0)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    stage = relationship("StageModel", foreign_keys=[stage_id], back_populates="attributes")
