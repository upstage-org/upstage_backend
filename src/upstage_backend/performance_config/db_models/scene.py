from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship

from upstage_backend.stages.db_models.stage import StageModel
from upstage_backend.users.db_models.user import UserModel


class SceneModel(BaseModel):
    __tablename__ = "scene"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scene_order: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True, default=0)
    scene_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(UserModel.id), nullable=False, default=0
    )
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(StageModel.id), nullable=False, default=0, index=True
    )
    owner: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[owner_id])
    stage: Mapped["StageModel"] = relationship("StageModel", foreign_keys=[stage_id])
