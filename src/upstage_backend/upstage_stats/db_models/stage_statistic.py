from datetime import datetime

from sqlalchemy import DateTime, Integer, String

from sqlalchemy.orm import Mapped, mapped_column
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel


class StageStatisticModel(BaseModel):
    """Latest live player/audience counts per stage.

    Aggregated by the upstage_stats MQTT worker from the retained
    ``<namespace>/<file_location>/statistics`` messages, and read by the GraphQL
    stage-list resolvers (foyer + stages table). This lets the foyer/list render
    counts from the query they already run instead of every row opening its own
    broker WebSocket (which caused connect/disconnect churn on search).
    """

    __tablename__ = "stage_statistics"

    # Keyed by the stage `file_location` (the same value the frontend uses as
    # `stageUrl` and that appears in the MQTT statistics topic).
    stage_url: Mapped[str] = mapped_column(String, primary_key=True)
    players: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audiences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
