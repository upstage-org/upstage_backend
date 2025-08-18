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
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from global_config.db_models.base import BaseModel


class AssetLicenseModel(BaseModel):
    __tablename__ = "asset_license"
    id = Column(BigInteger, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False, default=0)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    level = Column(Integer, nullable=False, default=0)
    permissions = Column(String, nullable=True)
