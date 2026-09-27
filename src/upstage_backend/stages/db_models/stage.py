from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DynamicMapped, Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel

if TYPE_CHECKING:
    from upstage_backend.stages.db_models.parent_stage import ParentStageModel
    from upstage_backend.users.db_models.user import UserModel


class StageModel(BaseModel):
    """
    Stage is yet another asset type, with its own attributes,
    but is broken out for convenience of group licensing/permissions.
    """

    __tablename__ = "stage"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upstage_user.id"), nullable=False, default=0, index=True
    )
    file_location: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_access: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[owner_id])
    attributes: DynamicMapped["StageAttributeModel"] = relationship(
        lambda: StageAttributeModel, lazy="dynamic", back_populates="stage"
    )
    # Ordered by parent_stage PK: assignMedia recreates the rows in the
    # order the client sent, so PK order IS the saved media order (drives
    # the on-stage toolbar ordering; without an explicit ORDER BY Postgres
    # may return updated rows in arbitrary order).
    assets: DynamicMapped["ParentStageModel"] = relationship(
        "ParentStageModel",
        lazy="dynamic",
        back_populates="stage",
        order_by="ParentStageModel.id",
    )

    @hybrid_property
    def cover(self):
        attribute = self.attributes.filter(StageAttributeModel.name == "cover").first()
        if attribute:
            return attribute.description
        return None

    @hybrid_property
    def visibility(self):
        attribute = self.attributes.filter(StageAttributeModel.name == "visibility").first()

        if attribute:
            return attribute.description == "true"

        return False

    @hybrid_property
    def status(self):
        attribute = self.attributes.filter(StageAttributeModel.name == "status").first()
        if attribute:
            return attribute.description
        return None

    @hybrid_property
    def playerAccess(self):
        # Mirrors the cover/visibility/status pattern: the value lives in the
        # stage_attribute table (name="playerAccess", description=<JSON string>).
        # Without this, the GraphQL Stage.playerAccess field always resolves to
        # null even when the attribute row exists, because get_stage_by_id only
        # merges hybrid properties (cover/visibility/status) into the response
        # dict and stage.to_dict() doesn't see attribute-table rows.
        attribute = self.attributes.filter(StageAttributeModel.name == "playerAccess").first()
        if attribute:
            return attribute.description
        return None
