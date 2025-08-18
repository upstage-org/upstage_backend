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
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from global_config.db_models.base import BaseModel
from sqlalchemy.orm import relationship


class PerformanceConfigModel(BaseModel):
    __tablename__ = "performance_config"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("upstage_user.id"), nullable=False, default=0)
    description = Column(Text, nullable=False)
    splash_screen_text = Column(Text, nullable=True, default=None)
    splash_screen_animation_urls = Column(Text, nullable=True, default=None)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    expires_on = Column(DateTime, nullable=False, default=None)

    owner = relationship("UserModel", foreign_keys=[owner_id])

    # def get_animation_urls(self):
    #     return self.splash_screen_animation_urls.split(",")
