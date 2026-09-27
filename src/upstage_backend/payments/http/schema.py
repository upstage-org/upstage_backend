from upstage_backend.payments.services.pdf_operator import create_receipt_base64

from ariadne import MutationType, QueryType
from graphql import GraphQLError
from pydantic import ValidationError
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.payments.services.payment import PaymentService
from upstage_backend.payments.http.validation import (
    PaymentIntentInput,
    OneTimePurchaseInput,
    CreateSubscriptionInput,
    ReceiptInput,
)
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN
from upstage_backend.users.services.user import UserService

query = QueryType()
mutation = MutationType()


# Public: anonymous visitors donate from the foyer. Captcha-gated in
# Production; amount / currency bounds live in PaymentIntentInput.
@mutation.field("paymentSecret")
async def get_payment_secret(_, info, input: PaymentIntentInput):
    try:
        dto = PaymentIntentInput(**input) if isinstance(input, dict) else input
    except ValidationError as exc:
        raise GraphQLError("Invalid donation amount or currency") from exc
    await UserService().verify_captcha_async(dto.token, info.context["request"])
    secret = await PaymentService().create_payment_intent_async(
        amount=dto.amount, currency=dto.currency
    )
    return secret or "Stripe failed"


# The four server-side card / subscription mutations below are not used by the
# studio UI (the donate flow uses Stripe Elements via paymentSecret). They
# handled raw card numbers and let anyone cancel any subscription id, so they
# are restricted to admins until they are removed or redesigned.
@mutation.field("oneTimePurchase")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
async def one_time_purchase(_, info, input: OneTimePurchaseInput):
    return await PaymentService().one_time_purchase(OneTimePurchaseInput(**input))


@mutation.field("createSubscription")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
async def create_subscription(_, info, input: CreateSubscriptionInput):
    return await PaymentService().create_subscription_process(CreateSubscriptionInput(**input))


@mutation.field("cancelSubscription")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
async def cancel_subscription(_, info, subscription_id: str):
    return await PaymentService().cancel_subscription(subscription_id)


@mutation.field("updateEmailCustomer")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
async def update_email_customer(_, info, customer_id: str, email: str):
    return await PaymentService().update_email_customer(customer_id, email)


# Public (issued right after an anonymous donation); the input is length-bound
# and escaped before it reaches ReportLab's markup parser.
@mutation.field("generateReceipt")
def resolve_generate_receipt(_, info, receivedFrom, date, description, amount):
    try:
        dto = ReceiptInput(
            receivedFrom=receivedFrom, date=date, description=description, amount=amount
        )
    except ValidationError as exc:
        raise GraphQLError("Invalid receipt details") from exc
    return create_receipt_base64(dto.receivedFrom, dto.date, dto.description, dto.amount)
