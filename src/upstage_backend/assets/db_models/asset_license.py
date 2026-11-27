from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel


class AssetLicenseModel(BaseModel):
    __tablename__ = "asset_license"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=False, default=0, index=True
    )
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    permissions: Mapped[str | None] = mapped_column(String, nullable=True)
