# -*- coding: iso8859-15 -*-
import os
import sys

from payments.services.pdf_operator import create_receipt_base64

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from ariadne import MutationType, QueryType, make_executable_schema
from ariadne.asgi import GraphQL
from studio_management.http.graphql import type_defs
from payments.services.payment import PaymentService
from payments.http.validation import (
    PaymentIntentInput,
    OneTimePurchaseInput,
    CreateSubscriptionInput,
)

query = QueryType()
mutation = MutationType()


@mutation.field("paymentSecret")
async def get_payment_secret(_, info, input: PaymentIntentInput):
    secret = PaymentService().create_payment_intent(**input)
    return secret or "Stripe failed"


@mutation.field("oneTimePurchase")
async def one_time_purchase(_, info, input: OneTimePurchaseInput):
    return await PaymentService().one_time_purchase(OneTimePurchaseInput(**input))


@mutation.field("createSubscription")
async def create_subscription(_, info, input: CreateSubscriptionInput):
    return await PaymentService().create_subscription_process(
        CreateSubscriptionInput(**input)
    )


@mutation.field("cancelSubscription")
async def cancel_subscription(_, info, subscription_id: str):
    return await PaymentService().cancel_subscription(subscription_id)


@mutation.field("updateEmailCustomer")
async def update_email_customer(_, info, customer_id: str, email: str):
    return await PaymentService().update_email_customer(customer_id, email)

@mutation.field("generateReceipt")
def resolve_generate_receipt(_, info, receivedFrom, date, description, amount):
    pdf_base64 = create_receipt_base64(receivedFrom, date, description, amount)
    
    return {
        "fileBase64": pdf_base64,
        "fileName": f"receipt_{receivedFrom.replace(' ', '_')}.pdf"
    }


schema = make_executable_schema(type_defs, query, mutation)
payment_graphql_app = GraphQL(schema, debug=True)
