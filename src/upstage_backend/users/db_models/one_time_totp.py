from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel

if TYPE_CHECKING:
    from upstage_backend.users.db_models.user import UserModel


class OneTimeTOTPModel(BaseModel):
    __tablename__ = "admin_one_time_totp_qr_url"

    # This is a one-time link to get the QR code for the TOTP secret, for Google Authenticator, etc.
    # Only admins use this, in the portal.
    # Today the table only holds password-reset codes (users/services/user.py):
    #   code          sha256 hex of the 6-digit code emailed to the user
    #   url           failed-attempt counter as text (column reused; adding a
    #                 real column needs an Alembic revision)
    #   recorded_time issue time; codes expire PASSWORD_RESET_TTL after it
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upstage_user.id"), unique=True, nullable=False, default=0
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Callable, not a call: `datetime.now()` here froze the timestamp at import
    # time, so every row carried the process start time and expiry was
    # impossible to enforce.
    recorded_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, default=utcnow
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True, default=True)
    user: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[user_id])
