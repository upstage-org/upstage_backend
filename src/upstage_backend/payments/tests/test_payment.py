# -*- coding: iso8859-15 -*-
import os
import sys

import asyncio
import pytest

from upstage_backend.payments.http.validation import OneTimePurchaseInput
from upstage_backend.payments.services.payment import PaymentService


@pytest.mark.anyio
class TestPaymentController:
    async def test_01_one_time_payment(self):
        otpi = OneTimePurchaseInput(
            cardNumber="4242424242424242",
            expYear="2025",
            expMonth="12",
            cvc="123",
            amount=100,
        )
        ps = PaymentService()
        result = await ps.one_time_purchase(otpi)
        assert result["success"] == True

    '''
    login_query = """
        mutation Login($payload: LoginInput!) {
            login(payload: $payload) {
                user_id
                access_token
                refresh_token
                role
                first_name
                groups {
                    id
                    name
                }
                username
                title
            }
        }
        """
    '''

    """
    async def test_01_login_with_invalid_credentials(self, client):
        variables = {
            "payload": {"username": Faker().email(), "password": "testpassword"}
        }
        response = client.post(
            "/graphql", json={"query": self.login_query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["message"] == "Incorrect username or password"
    """


if __name__ == "__main__":
    asyncio.run(TestPaymentController().test_01_one_time_payment())
