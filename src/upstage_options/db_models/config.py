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

from sqlalchemy import Column, DateTime, String, BigInteger, Text
from datetime import datetime
from global_config import BaseModel


class ConfigModel(BaseModel):
    """
    System configuration, such as the Terms of Service's URL, theme, global settings,...
    """

    __tablename__ = "config"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now())
