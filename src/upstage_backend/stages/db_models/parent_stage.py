from typing import TYPE_CHECKING
from sqlalchemy import Integer, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.assets.db_models.asset import AssetModel
    from upstage_backend.stages.db_models.stage import StageModel


class ParentStageModel(BaseModel):
    """
    This maps all 'children' in a hierarchy of assets for a stage.
    Assets also have children.
    Not yet sure if this maps only the first tier, or all assets to a stage.
    I could see the benefit of mapping them all, for quick asset collection.
    """

    __tablename__ = "parent_stage"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stage.id"), nullable=False, default=0, index=True
    )
    child_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=False, default=0, index=True
    )
    # Per-assignment exit (removal) animation; NULL = default ("vanish" / 1000 ms).
    exit_animation: Mapped[str | None] = mapped_column(String, nullable=True)
    exit_speed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped["StageModel"] = relationship(
        "StageModel", foreign_keys=[stage_id], back_populates="assets"
    )
    child_asset: Mapped["AssetModel"] = relationship(
        "AssetModel", foreign_keys=[child_asset_id], back_populates="stages"
    )
