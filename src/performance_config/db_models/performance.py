# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

import arrow
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
from global_config.db_models.base import BaseModel
from global_config.helpers.object import get_naive_utc_now
from sqlalchemy.orm import relationship


class PerformanceModel(BaseModel):
    __tablename__ = "performance"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    stage_id = Column(Integer, ForeignKey("stage.id"), nullable=False, default=0)
    created_on = Column(DateTime, nullable=False, default=lambda: get_naive_utc_now())
    saved_on = Column(DateTime, nullable=True)
    recording = Column(Boolean, nullable=False, default=False)
    duration = Column(BigInteger, nullable=True)  # duration in milliseconds from first to last event
    stage = relationship("StageModel", foreign_keys=[stage_id])
