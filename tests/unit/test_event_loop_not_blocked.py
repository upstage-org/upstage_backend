"""Slow third-party work must not freeze the server.

Resolvers run on the single uvicorn event loop. Three paths used to do slow
blocking work directly on it, freezing EVERY request until they returned:

* Cloudflare Turnstile verification on each production login/registration
  (``requests.post`` with no timeout: a stalled connection hung forever),
* media upload (base64 decode + disk write + synchronous ffmpeg, up to 30 s),
* every Stripe API call (synchronous client, 80 s default timeout).

Each now runs in a worker thread behind an async entry point. These tests
replace the slow primitive with one that blocks for BLOCK seconds, launch
several calls concurrently on one loop next to a 10 ms heartbeat, and assert
that the heartbeat never starves and that the calls overlap instead of
queueing. A control test proves the harness does detect a blocked loop.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import requests
import stripe
from graphql import GraphQLError

from upstage_backend.assets.services import asset as asset_module
from upstage_backend.assets.services.asset import AssetService
from upstage_backend.authentication.services.auth import AuthenticationService
from upstage_backend.payments.http import schema as payments_schema
from upstage_backend.payments.http.validation import (
    CreateSubscriptionInput,
    OneTimePurchaseInput,
)
from upstage_backend.payments.services.payment import PaymentService
from upstage_backend.users.db_models.user import SUPER_ADMIN, UserModel
from upstage_backend.users.services import user as user_module
from upstage_backend.users.services.user import UserService

BLOCK = 0.4  # seconds each fake third-party call blocks its thread
CONCURRENCY = 5  # <= default executor size, min(32, cpus + 4)
MAX_STALL = 0.15  # the loop must never go this long without running


def _measure(make_coro, n=CONCURRENCY):
    """Run n coroutines concurrently beside a heartbeat.

    Returns (results, longest heartbeat gap, wall-clock seconds)."""

    async def main():
        gaps, running = [], True

        async def heartbeat():
            last = time.perf_counter()
            while running:
                await asyncio.sleep(0.01)
                now = time.perf_counter()
                gaps.append(now - last)
                last = now

        beat = asyncio.create_task(heartbeat())
        await asyncio.sleep(0.03)
        started = time.perf_counter()
        results = await asyncio.gather(*(make_coro() for _ in range(n)), return_exceptions=True)
        elapsed = time.perf_counter() - started
        running = False
        await beat
        return results, max(gaps), elapsed

    return asyncio.run(main())


def _assert_loop_stayed_responsive(results, stall, elapsed):
    errors = [r for r in results if isinstance(r, BaseException)]
    assert errors == []
    assert stall < MAX_STALL, f"event loop starved for {stall:.2f}s"
    # Overlapping, not queued: far less than CONCURRENCY * BLOCK.
    assert elapsed < BLOCK * 2.5, f"calls ran serially ({elapsed:.2f}s)"


def _blocking(result=None):
    def fake(*args, **kwargs):
        fake.calls.append((args, kwargs))
        time.sleep(BLOCK)
        return result

    fake.calls = []
    return fake


def test_control_a_blocking_call_on_the_loop_is_detected():
    async def on_the_loop():
        time.sleep(BLOCK)

    _, stall, elapsed = _measure(on_the_loop, n=3)
    assert stall >= BLOCK
    assert elapsed >= BLOCK * 3 * 0.9


# ---------------------------------------------------------------- captcha


@pytest.fixture
def production_captcha(monkeypatch):
    monkeypatch.setattr(user_module, "ENV_TYPE", "Production")
    monkeypatch.setattr(user_module, "CLOUDFLARE_CAPTCHA_SECRETKEY", "secret")


def _request():
    return SimpleNamespace(
        headers={"CF-Connecting-IP": "203.0.113.9"}, client=SimpleNamespace(host="x")
    )


def test_concurrent_captcha_checks_do_not_block_the_loop(monkeypatch, production_captcha):
    fake_post = _blocking(SimpleNamespace(json=lambda: {"success": True}))
    monkeypatch.setattr(requests, "post", fake_post)

    outcome = _measure(lambda: UserService().verify_captcha_async("token", _request()))

    _assert_loop_stayed_responsive(*outcome)
    assert len(fake_post.calls) == CONCURRENCY
    assert all(kw["timeout"] == user_module.CAPTCHA_VERIFY_TIMEOUT for _, kw in fake_post.calls)


@pytest.mark.parametrize("failure", [requests.Timeout("stalled"), requests.ConnectionError("down")])
def test_captcha_outage_fails_closed_instead_of_hanging(monkeypatch, production_captcha, failure):
    def unreachable(*args, **kwargs):
        raise failure

    monkeypatch.setattr(requests, "post", unreachable)
    with pytest.raises(GraphQLError, match="could not verify the captcha"):
        asyncio.run(UserService().verify_captcha_async("token", _request()))


def test_captcha_rejection_still_rejects(monkeypatch, production_captcha):
    rejected = SimpleNamespace(
        json=lambda: {"success": False, "error-codes": ["invalid-input-response"]}
    )
    monkeypatch.setattr(requests, "post", lambda *a, **k: rejected)
    with pytest.raises(GraphQLError, match="not a human"):
        asyncio.run(UserService().verify_captcha_async("token", _request()))


def test_every_captcha_caller_uses_the_off_loop_check_before_any_db_work(monkeypatch):
    # The sentinel is raised by the async check. It can only surface if each
    # caller awaits it, and first: none of them has a database bound here.
    sentinel = GraphQLError("captcha ran first")
    monkeypatch.setattr(UserService, "verify_captcha_async", AsyncMock(side_effect=sentinel))

    def forbidden(*args, **kwargs):
        raise AssertionError("blocking verify_captcha called from async code")

    monkeypatch.setattr(UserService, "verify_captcha", forbidden)
    info = SimpleNamespace(context={"request": _request()})
    callers = [
        lambda: AuthenticationService().login(
            SimpleNamespace(token="t", username="u", password="p"), _request()
        ),
        lambda: UserService().create({"token": "t", "username": "u"}, _request()),
        lambda: payments_schema.get_payment_secret(None, info, {"amount": 100, "token": "token"}),
    ]
    for call in callers:
        with pytest.raises(GraphQLError, match="captcha ran first"):
            asyncio.run(call())


# ----------------------------------------------------------------- upload


def test_concurrent_video_uploads_do_not_block_the_loop(monkeypatch, tmp_path):
    fake_ffmpeg = _blocking()
    monkeypatch.setattr(asset_module, "storagePath", str(tmp_path))
    monkeypatch.setattr(asset_module, "extract_first_frame", fake_ffmpeg)
    admin = UserModel(role=SUPER_ADMIN, upload_limit=None)

    outcome = _measure(
        lambda: AssetService().upload_file_async(admin, "data:video/mp4;base64,AAAA", "clip.mp4")
    )

    _assert_loop_stayed_responsive(*outcome)
    assert len(fake_ffmpeg.calls) == CONCURRENCY
    written = {r["url"] for r in outcome[0]}
    assert len(written) == CONCURRENCY
    assert all((tmp_path / url).is_file() for url in written)


# ----------------------------------------------------------------- stripe


@pytest.fixture
def slow_stripe(monkeypatch):
    thing = SimpleNamespace(id="id_123", client_secret="secret_123")
    fakes = {
        (stripe.PaymentIntent, "create"): _blocking(thing),
        (stripe.Token, "create"): _blocking({"id": "tok_123"}),
        (stripe.Charge, "create"): _blocking({"paid": True}),
        (stripe.Subscription, "delete"): _blocking(thing),
        (stripe.Customer, "modify"): _blocking(thing),
        # Instant: the subscription flow chains four calls, one slow one is
        # enough to prove the whole chain left the loop.
        (stripe.PaymentMethod, "create"): lambda **kw: thing,
        (stripe.PaymentMethod, "attach"): lambda *a, **kw: thing,
        (stripe.Customer, "create"): lambda **kw: thing,
        (stripe.Price, "create"): lambda **kw: thing,
        (stripe.Subscription, "create"): _blocking(thing),
    }
    for (owner, name), fake in fakes.items():
        monkeypatch.setattr(owner, name, fake)


_CARD = dict(cardNumber="4242424242424242", expYear="2030", expMonth="12", cvc="123", amount=10)

STRIPE_ENTRY_POINTS = {
    "payment_intent": lambda: PaymentService().create_payment_intent_async(100, "usd"),
    "one_time_purchase": lambda: PaymentService().one_time_purchase(OneTimePurchaseInput(**_CARD)),
    "create_subscription": lambda: PaymentService().create_subscription_process(
        CreateSubscriptionInput(**_CARD, currency="usd", email="a@example.org", type="card")
    ),
    "cancel_subscription": lambda: PaymentService().cancel_subscription("sub_123"),
    "update_email_customer": lambda: PaymentService().update_email_customer(
        "cus_123", "a@example.org"
    ),
}


@pytest.mark.parametrize("entry_point", STRIPE_ENTRY_POINTS)
def test_concurrent_stripe_calls_do_not_block_the_loop(slow_stripe, entry_point):
    _assert_loop_stayed_responsive(*_measure(STRIPE_ENTRY_POINTS[entry_point]))
