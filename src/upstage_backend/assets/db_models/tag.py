# -*- coding: iso8859-15 -*-
import os
import sys

from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, String
from upstage_backend.global_config.db_models.base import BaseModel


class TagModel(BaseModel):
    __tablename__ = "tag"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
