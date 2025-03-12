# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from datetime import datetime
from global_config import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects import postgresql


class ConnectionStatModel(BaseModel):
    __tablename__ = "connection_stats"
    id = Column(Integer, primary_key=True)
    connected_id = Column(String, index=True)
    mqtt_timestamp = Column(DateTime, index=True)
    topic = Column(String)
    payload = Column(postgresql.JSON)
    created = Column(DateTime, default=datetime.now, index=True)
