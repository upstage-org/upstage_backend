from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from upstage_backend.users.db_models.user import UserModel


class PerformanceConfigModel(BaseModel):
    __tablename__ = "performance_config"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upstage_user.id"), nullable=False, default=0, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    splash_screen_text: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    splash_screen_animation_urls: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=None
    )

    owner: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[owner_id])

    # def get_animation_urls(self):
    #     return self.splash_screen_animation_urls.split(",")
