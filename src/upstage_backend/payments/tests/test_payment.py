import pytest
import stripe

from upstage_backend.payments.http.validation import OneTimeDonationInput
from upstage_backend.payments.services.payment import PaymentService


@pytest.mark.anyio
class TestPaymentController:
    async def test_01_one_time_payment(self, monkeypatch):
        # Stripe is stubbed: the suite must run without an API key or network.
        calls = {}

        def fake_token_create(**kwargs):
            calls["token"] = kwargs
            return {"id": "tok_test"}

        def fake_charge_create(**kwargs):
            calls["charge"] = kwargs
            return {"paid": True}

        monkeypatch.setattr(stripe.Token, "create", fake_token_create)
        monkeypatch.setattr(stripe.Charge, "create", fake_charge_create)

        otpi = OneTimeDonationInput(
            cardNumber="4242424242424242",
            expYear="2025",
            expMonth="12",
            cvc="123",
            amount=100,
        )
        ps = PaymentService()
        result = await ps.one_time_donation(otpi)
        assert result["success"] is True
        assert calls["token"]["card"] == {
            "number": "4242424242424242",
            "exp_month": 12,
            "exp_year": 2025,
            "cvc": "123",
        }
        assert calls["charge"]["source"] == "tok_test"
        assert calls["charge"]["amount"] == 100 * 100  # dollars -> cents
        assert calls["charge"]["currency"] == "usd"

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
