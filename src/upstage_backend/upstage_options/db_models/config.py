from sqlalchemy import DateTime, String, BigInteger, Integer, Text
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel


class ConfigModel(BaseModel):
    """
    System configuration, such as the Terms of Service's URL, theme, global settings,...
    """

    __tablename__ = "config"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Callable, not a call: `datetime.now()` here was evaluated once at import,
    # stamping every row created by that process with the process start time.
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
