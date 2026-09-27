from typing import TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import DynamicMapped, Mapped, mapped_column, relationship
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
    from upstage_backend.assets.db_models.asset_type import AssetTypeModel
    from upstage_backend.assets.db_models.asset_usage import AssetUsageModel
    from upstage_backend.assets.db_models.media_tag import MediaTagModel
    from upstage_backend.stages.db_models.parent_stage import ParentStageModel
    from upstage_backend.users.db_models.user import UserModel


class Previlege(Enum):
    NONE = 0
    OWNER = 1
    APPROVED = 2
    PENDING_APPROVAL = 3
    REQUIRE_APPROVAL = 4


class AssetModel(BaseModel):
    __tablename__ = "asset"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset_type.id"), nullable=False, default=0, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upstage_user.id"), nullable=False, default=0, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_location: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_on: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=utcnow)
    updated_on: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=utcnow)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    copyright_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dormant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    asset_type: Mapped["AssetTypeModel"] = relationship(
        "AssetTypeModel", foreign_keys=[asset_type_id]
    )
    owner: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[owner_id])
    asset_license: Mapped["AssetLicenseModel"] = relationship(
        "AssetLicenseModel", uselist=False, backref="asset"
    )
    stages: DynamicMapped["ParentStageModel"] = relationship(
        "ParentStageModel", lazy="dynamic", back_populates="child_asset"
    )
    tags: DynamicMapped["MediaTagModel"] = relationship(
        "MediaTagModel", lazy="dynamic", back_populates="asset"
    )
    permissions: DynamicMapped["AssetUsageModel"] = relationship(
        "AssetUsageModel", lazy="dynamic", back_populates="asset"
    )


class AvatarVoice:
    voice: str
    variant: str
    pitch: int
    speed: float
    amplitude: int


class Voice:
    def __init__(self, avatar=None, voice=None):
        self.voice = voice
        self.avatar = avatar

    voice: AvatarVoice
    avatar: AssetModel
