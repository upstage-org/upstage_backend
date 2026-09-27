from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.assets.db_models.asset import AssetModel


class AssetAttributeModel(BaseModel):
    """
    Attributes are the abilities of the asset: What the asset can do or be.
    For example, flip, rotate, draw, overlay, be opaque, dissolve, loop.
    Breaking out attributes and actions seemed like splitting hairs, and
    seems much easier in one table.
    """

    __tablename__ = "asset_attribute"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=False, default=0, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    asset: Mapped["AssetModel"] = relationship("AssetModel", foreign_keys=[asset_id])
