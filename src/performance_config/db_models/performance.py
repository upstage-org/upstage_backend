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
from global_config import BaseModel
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
