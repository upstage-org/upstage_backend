# -*- coding: iso8859-15 -*-
import os
import sys

from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, String, Text
from upstage_backend.global_config.db_models.base import BaseModel


class AssetTypeModel(BaseModel):
    """
    Asset type is Prop, Avatar/Sprite, Backdrop, for example.
    Over time we should be able to add more types or variations on
    existing types.
    """

    __tablename__ = "asset_type"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_location = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
