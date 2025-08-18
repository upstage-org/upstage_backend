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
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Text
from global_config.db_models.base import BaseModel
from sqlalchemy.orm import relationship

from stages.db_models.stage import StageModel
from users.db_models.user import UserModel


class SceneModel(BaseModel):
    __tablename__ = "scene"
    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    scene_order = Column(Integer, index=True, nullable=True, default=0)
    scene_preview = Column(Text, nullable=True)
    payload = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    active = Column(Boolean, nullable=False, default=True)
    owner_id = Column(Integer, ForeignKey(UserModel.id), nullable=False, default=0)
    stage_id = Column(Integer, ForeignKey(StageModel.id), nullable=False, default=0)
    owner = relationship("UserModel", foreign_keys=[owner_id])
    stage = relationship("StageModel", foreign_keys=[stage_id])
