# -*- coding: iso8859-15 -*-
from typing import Optional
from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    token: Optional[str] = Field(None, min_length=5, max_length=10000)
    username: str = Field(...,max_length=100)
    password: str = Field(...,max_length=256)
