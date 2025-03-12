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

import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects import postgresql

from global_config import BaseModel


class EventModel(BaseModel):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    topic = Column(String)
    mqtt_timestamp = Column(Float, index=True)
    performance_id = Column(Integer, index=True)
    payload = Column(postgresql.JSON)
    created = Column(DateTime, default=datetime.datetime.now, index=True)
