# -*- coding: iso8859-15 -*-
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

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
    stage_url = Column(String, primary_key=True)
    players = Column(Integer, nullable=False, default=0)
    audiences = Column(Integer, nullable=False, default=0)
    updated_on = Column(DateTime, nullable=False, default=datetime.now)
