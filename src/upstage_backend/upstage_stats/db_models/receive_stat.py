# -*- coding: iso8859-15 -*-
import os
import sys

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from upstage_backend.global_config.db_models.base import BaseModel
from sqlalchemy.dialects import postgresql


class ReceiveStatModel(BaseModel):
    __tablename__ = "receive_stats"
    id = Column(Integer, primary_key=True)
    received_id = Column(String, index=True)
    mqtt_timestamp = Column(DateTime, index=True)
    topic = Column(String)
    payload = Column(postgresql.JSON)
    created = Column(DateTime, default=datetime.now, index=True)
