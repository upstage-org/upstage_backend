# -*- coding: iso8859-15 -*-
import os
import sys

from sqlalchemy import Column, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from upstage_backend.global_config.db_models.base import BaseModel
from upstage_backend.assets.db_models.tag import TagModel


class MediaTagModel(BaseModel):
    __tablename__ = "media_tag"
    id = Column(BigInteger, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    tag_id = Column(Integer, ForeignKey("tag.id"), nullable=False, default=0)
    asset = relationship("AssetModel", foreign_keys=[asset_id], back_populates="tags")
    tag = relationship("TagModel", foreign_keys=[tag_id])
