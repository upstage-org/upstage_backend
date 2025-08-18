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
from sqlalchemy import BigInteger, Column, DateTime, String
from global_config.db_models.base import BaseModel


class TagModel(BaseModel):
    __tablename__ = "tag"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
