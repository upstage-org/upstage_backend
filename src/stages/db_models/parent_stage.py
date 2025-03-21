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
from assets.db_models.asset import AssetModel


class ParentStageModel(BaseModel):
    """
    This maps all 'children' in a hierarchy of assets for a stage.
    Assets also have children.
    Not yet sure if this maps only the first tier, or all assets to a stage.
    I could see the benefit of mapping them all, for quick asset collection.
    """

    __tablename__ = "parent_stage"
    id = Column(BigInteger, primary_key=True)
    stage_id = Column(Integer, ForeignKey("stage.id"), nullable=False, default=0)
    child_asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    stage = relationship("StageModel", foreign_keys=[stage_id], back_populates="assets")
    child_asset = relationship(
        "AssetModel", foreign_keys=[child_asset_id], back_populates="stages"
    )
