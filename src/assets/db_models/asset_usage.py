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
from enum import Enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from global_config.db_models.base import BaseModel


class AssetUsageModel(BaseModel):
    __tablename__ = "asset_usage"
    id = Column(BigInteger, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    user_id = Column(Integer, ForeignKey("upstage_user.id"), nullable=False, default=0)
    approved = Column(Boolean, nullable=False, default=False)
    seen = Column(Boolean, nullable=False, default=False)
    note = Column(String, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    user = relationship("UserModel", foreign_keys=[user_id])
    asset = relationship("AssetModel", foreign_keys=[asset_id])


class NotificationType(Enum):
    MEDIA_USAGE = 1


class Notification:
    def __init__(self, type, mediaUsage):
        self.type = type
        self.mediaUsage = mediaUsage

    type = NotificationType
    mediaUsage = AssetUsageModel
