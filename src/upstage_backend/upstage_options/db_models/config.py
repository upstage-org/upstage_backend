from sqlalchemy import Column, DateTime, String, BigInteger, Integer, Text
from datetime import datetime
from upstage_backend.global_config.db_models.base import BaseModel


class ConfigModel(BaseModel):
    """
    System configuration, such as the Terms of Service's URL, theme, global settings,...
    """

    __tablename__ = "config"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    # Callable, not a call: `datetime.now()` here was evaluated once at import,
    # stamping every row created by that process with the process start time.
    created_on = Column(DateTime, nullable=False, default=datetime.now)
