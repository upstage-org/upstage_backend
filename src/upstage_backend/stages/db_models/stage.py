# -*- coding: iso8859-15 -*-

from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from upstage_backend.global_config.db_models.base import BaseModel
from upstage_backend.stages.db_models.stage_attribute import StageAttributeModel


class StageModel(BaseModel):
    """
    Stage is yet another asset type, with its own attributes,
    but is broken out for convenience of group licensing/permissions.
    """

    __tablename__ = "stage"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("upstage_user.id"), nullable=False, default=0)
    file_location = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    last_access = Column(DateTime, nullable=True)
    owner = relationship("UserModel", foreign_keys=[owner_id])
    attributes = relationship(lambda: StageAttributeModel, lazy="dynamic", back_populates="stage")
    # Ordered by parent_stage PK: assignMedia recreates the rows in the
    # order the client sent, so PK order IS the saved media order (drives
    # the on-stage toolbar ordering; without an explicit ORDER BY Postgres
    # may return updated rows in arbitrary order).
    assets = relationship(
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
