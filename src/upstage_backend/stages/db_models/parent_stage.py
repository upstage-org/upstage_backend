# -*- coding: iso8859-15 -*-

from sqlalchemy import Column, Integer, BigInteger, ForeignKey, String
from sqlalchemy.orm import relationship
from upstage_backend.global_config.db_models.base import BaseModel


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
    # Per-assignment exit (removal) animation; NULL = default ("vanish" / 1000 ms).
    exit_animation = Column(String, nullable=True)
    exit_speed = Column(Integer, nullable=True)
    stage = relationship("StageModel", foreign_keys=[stage_id], back_populates="assets")
    child_asset = relationship("AssetModel", foreign_keys=[child_asset_id], back_populates="stages")
