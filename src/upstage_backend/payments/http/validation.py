# -*- coding: iso8859-15 -*-
from typing import Optional

from pydantic import BaseModel, Field


class PaymentIntentInput(BaseModel):
    amount: int = Field(...)
    currency: str = Field(default="usd")
    token: Optional[str] = Field(None, min_length=5, max_length=10000)


class OneTimePurchaseInput(BaseModel):
    cardNumber: str = Field(...)
    expYear: str = Field(...)
    expMonth: str = Field(...)
    cvc: str = Field(...)
    amount: float = Field(...)


class CreateSubscriptionInput(BaseModel):
    cardNumber: str = Field(...)
    expYear: str = Field(...)
    expMonth: str = Field(...)
    cvc: str = Field(...)
    amount: float = Field(...)
    currency: str = Field(...)
    email: str = Field(...)
    type: str = Field(...)
