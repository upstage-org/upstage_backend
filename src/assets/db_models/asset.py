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
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from global_config import BaseModel
from assets.db_models.asset_type import AssetTypeModel
from assets.db_models.asset_license import AssetLicenseModel
from assets.db_models.media_tag import MediaTagModel
from assets.db_models.asset_usage import AssetUsageModel

class Previlege(Enum):
    NONE = 0
    OWNER = 1
    APPROVED = 2
    PENDING_APPROVAL = 3
    REQUIRE_APPROVAL = 4


class AssetModel(BaseModel):
    __tablename__ = "asset"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    asset_type_id = Column(
        Integer, ForeignKey("asset_type.id"), nullable=False, default=0
    )
    owner_id = Column(Integer, ForeignKey("upstage_user.id"), nullable=False, default=0)
    description = Column(Text, nullable=True)
    file_location = Column(Text, nullable=False)
    created_on = Column(TIMESTAMP(timezone=True), default=datetime.now)
    updated_on = Column(TIMESTAMP(timezone=True), default=datetime.now)
    size = Column(BigInteger, nullable=False, default=0)
    copyright_level = Column(Integer, nullable=False, default=0)
    dormant = Column(Boolean, nullable=False, default=False)
    asset_type = relationship("AssetTypeModel", foreign_keys=[asset_type_id])
    owner = relationship("UserModel", foreign_keys=[owner_id])
    asset_license = relationship("AssetLicenseModel", uselist=False, backref="asset")
    stages = relationship(
        "ParentStageModel", lazy="dynamic", back_populates="child_asset"
    )
    tags = relationship("MediaTagModel", lazy="dynamic", back_populates="asset")
    permissions = relationship(
        "AssetUsageModel", lazy="dynamic", back_populates="asset"
    )


class AvatarVoice:
    voice: str
    variant: str
    pitch: int
    speed: float
    amplitude: int


class Voice:
    voice: AvatarVoice
    avatar: AssetModel
