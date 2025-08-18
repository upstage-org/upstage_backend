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
from sqlalchemy import BigInteger, Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from global_config.db_models.base import BaseModel
from users.db_models.user import UserModel


class UserSessionModel(BaseModel):
    __tablename__ = "user_session"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey(UserModel.id, deferrable=True, initially="DEFERRED"),
        nullable=False,
        index=True,
    )
    access_token = Column(Text, default=None)
    refresh_token = Column(Text, default=None)
    recorded_time = Column(
        DateTime, nullable=False, index=True, default=datetime.utcnow
    )
    app_version = Column(Text, default=None)
    app_os_type = Column(Text, default=None)
    app_os_version = Column(Text, default=None)
    app_device = Column(Text, default=None)
    user = relationship(UserModel, foreign_keys=[user_id])
