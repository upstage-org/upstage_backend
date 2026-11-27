from typing import TYPE_CHECKING
from sqlalchemy import Integer, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.assets.db_models.asset import AssetModel
    from upstage_backend.assets.db_models.tag import TagModel


class MediaTagModel(BaseModel):
    __tablename__ = "media_tag"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=False, default=0, index=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tag.id"), nullable=False, default=0, index=True
    )
    asset: Mapped["AssetModel"] = relationship(
        "AssetModel", foreign_keys=[asset_id], back_populates="tags"
    )
    tag: Mapped["TagModel"] = relationship("TagModel", foreign_keys=[tag_id])
