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

from sqlalchemy import Column, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from global_config import BaseModel
from assets.db_models.tag import TagModel


class MediaTagModel(BaseModel):
    __tablename__ = "media_tag"
    id = Column(BigInteger, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    tag_id = Column(Integer, ForeignKey("tag.id"), nullable=False, default=0)
    asset = relationship("AssetModel", foreign_keys=[asset_id], back_populates="tags")
    tag = relationship("TagModel", foreign_keys=[tag_id])
