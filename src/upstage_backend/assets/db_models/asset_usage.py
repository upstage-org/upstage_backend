# -*- coding: iso8859-15 -*-

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from upstage_backend.global_config.db_models.base import BaseModel


class AssetUsageModel(BaseModel):
    __tablename__ = "asset_usage"
    id = Column(BigInteger, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    user_id = Column(Integer, ForeignKey("upstage_user.id"), nullable=False, default=0)
    approved = Column(Boolean, nullable=False, default=False)
    # Per-recipient dismissal flags for the three-way bell:
    #   * owner_seen     – the asset's owner has acted on / dismissed this row.
    #   * requester_seen – the requester (`user_id`) has dismissed the result.
    # Bell queries filter:
    #   * pending request  : approved=False  AND owner.id=me     AND owner_seen=False
    #   * acknowledgement  : approved=True   AND owner.id=me     AND owner_seen=False
    #   * approval result  : approved=True   AND user_id=me      AND requester_seen=False
    # The dismissNotification mutation flips whichever flag applies
    # to the caller's role on the row.
    owner_seen = Column(Boolean, nullable=False, default=False)
    requester_seen = Column(Boolean, nullable=False, default=False)
    note = Column(String, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    user = relationship("UserModel", foreign_keys=[user_id])
    asset = relationship("AssetModel", foreign_keys=[asset_id])


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
