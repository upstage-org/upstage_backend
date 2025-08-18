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
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from global_config.db_models.base import BaseModel


class OneTimeTOTPModel(BaseModel):
    __tablename__ = "admin_one_time_totp_qr_url"

    # This is a one-time link to get the QR code for the TOTP secret, for Google Authenticator, etc.
    # Only admins use this, in the portal.
    id = Column(BigInteger, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("upstage_user.id"), unique=True, nullable=False, default=0
    )
    url = Column(Text, nullable=False, default="")
    code = Column(Text, nullable=False, default="")
    recorded_time = Column(DateTime, nullable=False, index=True, default=datetime.now())
    active = Column(Boolean, nullable=False, index=True, default=True)
    user = relationship("UserModel", foreign_keys=[user_id])
