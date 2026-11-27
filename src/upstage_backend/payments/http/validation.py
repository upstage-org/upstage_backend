from typing import Optional

from pydantic import BaseModel, Field


class PaymentIntentInput(BaseModel):
    # Stripe minor units (cents). Bounds keep an anonymous caller from
    # creating absurd or sub-minimum intents against the live account.
    amount: int = Field(..., ge=50, le=5_000_000)
    currency: str = Field(default="usd", pattern=r"^[a-z]{3}$")
    token: Optional[str] = Field(None, min_length=5, max_length=10000)


class ReceiptInput(BaseModel):
    receivedFrom: str = Field(..., min_length=1, max_length=100)
    date: str = Field(..., min_length=1, max_length=40)
    description: str = Field(..., min_length=1, max_length=200)
    amount: str = Field(..., min_length=1, max_length=20)


class OneTimeDonationInput(BaseModel):
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
