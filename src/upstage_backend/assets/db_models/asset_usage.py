from typing import TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.assets.db_models.asset import AssetModel
    from upstage_backend.users.db_models.user import UserModel


class AssetUsageModel(BaseModel):
    __tablename__ = "asset_usage"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=False, default=0, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upstage_user.id"), nullable=False, default=0, index=True
    )
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Per-recipient dismissal flags for the three-way bell:
    #   * owner_seen     – the asset's owner has acted on / dismissed this row.
    #   * requester_seen – the requester (`user_id`) has dismissed the result.
    # Bell queries filter:
    #   * pending request  : approved=False  AND owner.id=me     AND owner_seen=False
    #   * acknowledgement  : approved=True   AND owner.id=me     AND owner_seen=False
    #   * approval result  : approved=True   AND user_id=me      AND requester_seen=False
    # The dismissNotification mutation flips whichever flag applies
    # to the caller's role on the row.
    owner_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requester_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    user: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[user_id])
    asset: Mapped["AssetModel"] = relationship("AssetModel", foreign_keys=[asset_id])


class NotificationType(Enum):
    # Strict permission request awaiting owner approval (pre-existing).
    MEDIA_USAGE = 1
    # Owner approved a strict request; requester sees this until dismissed.
    PERMISSION_APPROVED = 2
    # Player invoked the "use with acknowledgement" flow on a non-strict
    # asset; owner sees this FYI until dismissed.
    MEDIA_ACKNOWLEDGEMENT = 3


class Notification:
    def __init__(self, type, mediaUsage):
        self.type = type
        self.mediaUsage = mediaUsage

    type = NotificationType
    mediaUsage = AssetUsageModel
