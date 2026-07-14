# -*- coding: iso8859-15 -*-

from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from upstage_backend.global_config.db_models.base import BaseModel


class AssetLicenseModel(BaseModel):
    __tablename__ = "asset_license"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    level = Column(Integer, nullable=False, default=0)
    permissions = Column(String, nullable=True)
