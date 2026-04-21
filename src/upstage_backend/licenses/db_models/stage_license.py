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
)
from upstage_backend.global_config.db_models.base import BaseModel
from upstage_backend.stages.db_models.stage import StageModel
from sqlalchemy.orm import relationship


class StageLicenseModel(BaseModel):
    """
    Stage is yet another asset, but broken out as the 'root' in the hierarchy.
    One can grant a license to everything under a stage, or any other asset,
    to make licensing easier.
    """

    __tablename__ = "stage_license"
    id = Column(BigInteger, primary_key=True)
    stage_id = Column(Integer, ForeignKey(StageModel.id), nullable=False, default=0)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_on = Column(DateTime, nullable=True)
    access_path = Column(String, nullable=False, unique=True)
    grant_recursively = Column(Boolean, nullable=False, default=False)
    stage = relationship("StageModel", foreign_keys=[stage_id])
