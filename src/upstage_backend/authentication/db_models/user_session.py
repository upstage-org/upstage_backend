from datetime import datetime
from sqlalchemy import BigInteger, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel
from upstage_backend.users.db_models.user import UserModel


class UserSessionModel(BaseModel):
    __tablename__ = "user_session"
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(UserModel.id, deferrable=True, initially="DEFERRED"),
        nullable=False,
        index=True,
    )
    access_token: Mapped[str | None] = mapped_column(Text, default=None)
    refresh_token: Mapped[str | None] = mapped_column(Text, default=None)
    recorded_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, default=utcnow
    )
    app_version: Mapped[str | None] = mapped_column(Text, default=None)
    app_os_type: Mapped[str | None] = mapped_column(Text, default=None)
    app_os_version: Mapped[str | None] = mapped_column(Text, default=None)
    app_device: Mapped[str | None] = mapped_column(Text, default=None)
    user: Mapped["UserModel"] = relationship(UserModel, foreign_keys=[user_id])
