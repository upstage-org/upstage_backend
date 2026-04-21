# -*- coding: iso8859-15 -*-
import os
import sys

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from upstage_backend.global_config.db_models.base import BaseModel
from sqlalchemy.orm import relationship


class PerformanceModel(BaseModel):
    __tablename__ = "performance"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    stage_id = Column(Integer, ForeignKey("stage.id"), nullable=False, default=0)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    saved_on = Column(DateTime, nullable=True)
    recording = Column(Boolean, nullable=False, default=False)
    stage = relationship("StageModel", foreign_keys=[stage_id])
