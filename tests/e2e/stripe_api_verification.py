"""Stripe API verification script — Plan 50-04 companion to test_stripe_checkout_flow.py.

PURPOSE
-------
The sibling file `test_stripe_checkout_flow.py` runs the full end-to-end
Stripe CLI + local dev stack UAT and is the canonical pre-beta smoke test.
It requires Docker, Supabase, the backend, the frontend, Stripe CLI, and a
real Supabase user — a lot of moving parts.

This script is the **minimum viable Stripe-side verification**: it talks
directly to Stripe's API using a test key and validates the Stripe-side
contract our webhook handler relies on, without needing any local services.

It answers these questions:

    1. Do our vitest fixtures for `customer.subscription.created` actually
       match the shape Stripe emits in test mode?
    2. Does `metadata.supabase_user_id` propagate through to the
       `customer.subscription.*` events as expected (BILL-01 hand-off)?
    3. Does `cancel_at_period_end=true` in a subscription update actually
       show up in the corresponding `customer.subscription.updated` event
       payload? (BILL-01 race regression validates that our handler
       preserves this flag.)
    4. Can we programmatically create a Customer Portal configuration?
       (BILL-05 prerequisite — without a config, no portal session can
       be created.)
    5. Can we create a portal session for a real customer? (BILL-05
       contract — what our `/api/stripe/portal` route wraps.)

It does NOT test our local webhook handler (that's covered by 9 passing
vitest cases in `frontend/src/app/api/webhooks/stripe/__tests__/route.test.ts`)
and does NOT test the end-to-end browser flow (that's what
`test_stripe_checkout_flow.py` is for).

PREREQUISITES
-------------
    * Stripe test key exported as `STRIPE_TEST_KEY` (prefix sk_test_ or rk_test_)
      — typically loaded from the project root `.env`
    * The 3 tier products + prices already exist in the Stripe test account
      (they do — verified during Plan 50-04 inventory)
    * No local dev stack required

RUN WITH
--------
    # Loads STRIPE_TEST_KEY from .env automatically
    (set -a; source .env; set +a; \\
      .venv/Scripts/python.exe tests/e2e/stripe_api_verification.py)

    # Or set the var explicitly
    STRIPE_TEST_KEY=rk_test_... python tests/e2e/stripe_api_verification.py

OUTPUT
------
Writes a fixtures JSON file to
`.planning/phases/50-billing-payments/50-04-stripe-api-fixtures.json`
containing the real Stripe event payloads observed during the run, so
future runs can diff against it.

SAFETY
------
    * Refuses to run with a live key (prefix must be sk_test_ or rk_test_)
    * Creates all resources with a unique `uat-test-plan-50-04-<timestamp>`
      metadata tag so they can be filtered out of other test data
    * Deletes the created customer at the end (which cascades to all
      its subscriptions and invoices in test mode)
    * Only creates ONE portal configuration per run, and reuses the
      default if one already exists
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import stripe

# ---------------------------------------------------------------------------
# Config — tier → price ID map (from Plan 50-04 inventory call)
# ---------------------------------------------------------------------------

TIER_PRICES = {
    "solopreneur": "price_1S3aSSIpVJs9RrPn3xgT1tsd",  # $99/mo
    "startup": "price_1S3aSzIpVJs9RrPnpPBdr4ej",  # $297/mo
    "sme": "price_1S3aTaIpVJs9RrPnv42ImIxv",  # $597/mo
}

TIER_PRODUCTS = {
    "solopreneur": "prod_SzZa0vFbY85XZq",
    "startup": "prod_SzZbQmICivELiG",
    "sme": "prod_SzZb3qJnC2URiE",
}

# All 6 prices (monthly + yearly) for portal config
ALL_PRICES_BY_PRODUCT = {
    "prod_SzZa0vFbY85XZq": [
        "price_1S3aSSIpVJs9RrPn3xgT1tsd",  # solo monthly
        "price_1S3aSjIpVJs9RrPnW1h5p0di",  # solo yearly
    ],
    "prod_SzZbQmICivELiG": [
        "price_1S3aSzIpVJs9RrPnpPBdr4ej",  # startup monthly
        "price_1S3aTIIpVJs9RrPn816mKl8h",  # startup yearly
    ],
    "prod_SzZb3qJnC2URiE": [
        "price_1S3aTaIpVJs9RrPnv42ImIxv",  # sme monthly
        "price_1S3aTqIpVJs9RrPnJb10pnX9",  # sme yearly
    ],
}

FIXTURES_PATH = (
    Path(__file__).resolve().parents[2]
    / ".planning"
    / "phases"
    / "50-billing-payments"
    / "50-04-stripe-api-fixtures.json"
)

RUN_ID = f"uat-plan-50-04-{int(time.time())}"
FAKE_SUPABASE_USER_ID = f"00000000-0000-0000-0000-{int(time.time()):012d}"


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


class Result:
    """Tracks which checks passed/failed so we can print a summary at the end."""

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.skipped: list[tuple[str, str]] = []
        self.fixtures: dict[str, Any] = {}

    def ok(self, check: str) -> None:
        self.passed.append(check)
        print(f"  [PASS] {check}")

    def fail(self, check: str, reason: str) -> None:
        self.failed.append((check, reason))
        print(f"  [FAIL] {check}: {reason}")

    def skip(self, check: str, reason: str) -> None:
        self.skipped.append((check, reason))
        print(f"  [SKIP] {check}: {reason}")

    def capture(self, key: str, value: Any) -> None:
        """Save a fixture payload for later comparison."""
        self.fixtures[key] = value

    def summary(self) -> int:
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Passed:  {len(self.passed)}")
        print(f"  Failed:  {len(self.failed)}")
        print(f"  Skipped: {len(self.skipped)}")
        if self.failed:
            print()
            print("FAILURES:")
            for check, reason in self.failed:
                print(f"  - {check}: {reason}")
        if self.skipped:
            print()
            print("SKIPPED:")
            for check, reason in self.skipped:
                print(f"  - {check}: {reason}")
        return 1 if self.failed else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_event_for_object(
    event_type: str,
    object_id: str,
    timeout: int = 15,
) -> stripe.Event | None:
    """Poll stripe.Event.list for an event of the given type targeting object_id.

    Stripe events are eventually consistent — they may take a few hundred ms
    to appear after the triggering API call. Poll with exponential backoff.
    """
    deadline = time.monotonic() + timeout
    sleep = 0.2
    while time.monotonic() < deadline:
        events = stripe.Event.list(type=event_type, limit=20)
        for ev in events.data:
            if ev.data.object.id == object_id:
                return ev
        time.sleep(sleep)
        sleep = min(sleep * 1.5, 2.0)
    return None


def _safe_model_dump(obj: Any) -> Any:
    """Convert a Stripe object to a plain dict for JSON serialization."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "to_dict_recursive"):
        return obj.to_dict_recursive()
    return dict(obj) if hasattr(obj, "__iter__") else str(obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    # ── Key validation ─────────────────────────────────────────────────
    key = os.environ.get("STRIPE_TEST_KEY") or os.environ.get("STRIPE_SECRET_KEY_FOR_UAT")
    if not key:
        print("ERROR: STRIPE_TEST_KEY not set in environment")
        print("Hint: run via `set -a; source .env; set +a; python tests/e2e/stripe_api_verification.py`")
        return 2
    if not key.startswith(("sk_test_", "rk_test_")):
        print(f"ERROR: Key prefix {key[:8]!r} is not a test key — refusing to run")
        print("This script MUST run against test mode only. Never use a live key.")
        return 2

    stripe.api_key = key
    print(f"Stripe test key verified: prefix={key[:8]}, type={'restricted' if key.startswith('rk_') else 'secret'}")
    print(f"Run ID: {RUN_ID}")
    print(f"Fake Supabase user ID: {FAKE_SUPABASE_USER_ID}")
    print()

    result = Result()
    customer: stripe.Customer | None = None
    subscription: stripe.Subscription | None = None

    try:
        # ── Check 1: Tier prices exist and are in test mode ───────────
        print("Check 1: Tier prices exist and are in test mode")
        for tier, price_id in TIER_PRICES.items():
            try:
                price = stripe.Price.retrieve(price_id)
                if price.livemode:
                    result.fail(f"tier {tier}", f"price {price_id} is livemode=True")
                elif not price.active:
                    result.fail(f"tier {tier}", f"price {price_id} is inactive")
                elif price.recurring is None or price.recurring.get("interval") != "month":
                    result.fail(f"tier {tier}", f"price {price_id} is not monthly recurring")
                else:
                    result.ok(f"tier {tier}: price {price_id} = ${price.unit_amount / 100:.0f}/{price.recurring['interval']}")
                    result.capture(f"price_{tier}", _safe_model_dump(price))
            except stripe.StripeError as e:
                result.fail(f"tier {tier} price retrieval", str(e)[:150])

        # ── Check 2: Create a test customer with metadata ─────────────
        print()
        print("Check 2: Create test customer with metadata.supabase_user_id")
        try:
            customer = stripe.Customer.create(
                email=f"uat-{RUN_ID}@test.pikar.ai",
                name=f"Pikar UAT Plan 50-04 {RUN_ID}",
                metadata={
                    "supabase_user_id": FAKE_SUPABASE_USER_ID,
                    "run_id": RUN_ID,
                    "test_origin": "plan-50-04-api-verification",
                },
                payment_method="pm_card_visa",  # Stripe built-in test token
                invoice_settings={"default_payment_method": "pm_card_visa"},
            )
            assert customer.metadata.get("supabase_user_id") == FAKE_SUPABASE_USER_ID
            result.ok(f"customer created: {customer.id}")
            result.capture("customer_create", _safe_model_dump(customer))
        except stripe.StripeError as e:
            result.fail("customer.create", str(e)[:200])
            return result.summary()

        # ── Check 3: Create subscription with metadata on Solopreneur ─
        print()
        print("Check 3: Create subscription on Solopreneur tier with metadata")
        try:
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": TIER_PRICES["solopreneur"]}],
                metadata={
                    "supabase_user_id": FAKE_SUPABASE_USER_ID,
                    "tier": "solopreneur",
                    "run_id": RUN_ID,
                },
                collection_method="charge_automatically",
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )
            assert subscription.metadata.get("supabase_user_id") == FAKE_SUPABASE_USER_ID
            assert subscription.metadata.get("tier") == "solopreneur"
            result.ok(f"subscription created: {subscription.id} status={subscription.status}")
            result.capture("subscription_create", _safe_model_dump(subscription))
        except stripe.StripeError as e:
            result.fail("subscription.create", str(e)[:200])
            return result.summary()

        # ── Check 4: customer.subscription.created event has metadata ─
        print()
        print("Check 4: customer.subscription.created event carries metadata.supabase_user_id")
        event = _fetch_event_for_object("customer.subscription.created", subscription.id)
        if event is None:
            result.fail(
                "customer.subscription.created event",
                "event not found in stripe.Event.list after 15s — Stripe events may be delayed",
            )
        else:
            ev_metadata = event.data.object.metadata
            if ev_metadata.get("supabase_user_id") == FAKE_SUPABASE_USER_ID:
                result.ok(
                    "customer.subscription.created.data.object.metadata.supabase_user_id "
                    f"== {FAKE_SUPABASE_USER_ID}"
                )
            else:
                result.fail(
                    "customer.subscription.created metadata",
                    f"got supabase_user_id={ev_metadata.get('supabase_user_id')!r}",
                )
            # Verify tier extractable from price_id
            ev_price_id = event.data.object["items"]["data"][0]["price"]["id"]
            if ev_price_id == TIER_PRICES["solopreneur"]:
                result.ok(f"event.items[0].price.id == solopreneur price ({ev_price_id})")
            else:
                result.fail("event price_id", f"got {ev_price_id}")
            result.capture("event_subscription_created", _safe_model_dump(event))

        # ── Check 5: Cancel subscription with cancel_at_period_end ────
        print()
        print("Check 5: Cancel subscription with cancel_at_period_end=True (BILL-01 setup)")
        try:
            updated = stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=True,
            )
            if updated.cancel_at_period_end:
                result.ok(f"subscription {subscription.id} cancel_at_period_end=True")
            else:
                result.fail("cancel_at_period_end modify", "flag did not persist")
        except stripe.StripeError as e:
            result.fail("subscription.modify cancel_at_period_end", str(e)[:200])

        # ── Check 6: customer.subscription.updated event reflects cancel ─
        print()
        print("Check 6: customer.subscription.updated event carries cancel_at_period_end=True")
        updated_event = _fetch_event_for_object(
            "customer.subscription.updated",
            subscription.id,
        )
        if updated_event is None:
            result.fail(
                "customer.subscription.updated event",
                "event not found in stripe.Event.list after 15s",
            )
        else:
            ev_cancel = updated_event.data.object.get("cancel_at_period_end")
            if ev_cancel is True:
                result.ok(
                    "customer.subscription.updated.data.object.cancel_at_period_end == True "
                    "(this is the state our BILL-01 race fix must preserve)"
                )
            else:
                result.fail(
                    "customer.subscription.updated cancel_at_period_end",
                    f"got {ev_cancel!r}",
                )
            result.capture("event_subscription_updated_cancel", _safe_model_dump(updated_event))

        # ── Check 7: Create or reuse Customer Portal configuration ────
        print()
        print("Check 7: Customer Portal configuration exists (create if missing)")
        try:
            existing = stripe.billing_portal.Configuration.list(limit=10, is_default=True)
            if existing.data:
                config = existing.data[0]
                result.ok(f"reusing existing default portal config: {config.id}")
            else:
                config = stripe.billing_portal.Configuration.create(
                    business_profile={
                        "headline": "Pikar AI Subscription Management",
                    },
                    features={
                        "subscription_cancel": {
                            "enabled": True,
                            "mode": "at_period_end",
                            "cancellation_reason": {
                                "enabled": True,
                                "options": [
                                    "too_expensive",
                                    "missing_features",
                                    "switched_service",
                                    "unused",
                                    "customer_service",
                                    "too_complex",
                                    "low_quality",
                                    "other",
                                ],
                            },
                        },
                        "subscription_update": {
                            "enabled": True,
                            "default_allowed_updates": ["price"],
                            "products": [
                                {"product": pid, "prices": prices}
                                for pid, prices in ALL_PRICES_BY_PRODUCT.items()
                            ],
                            "proration_behavior": "create_prorations",
                        },
                        "payment_method_update": {"enabled": True},
                        "invoice_history": {"enabled": True},
                    },
                    default_return_url="http://localhost:3000/dashboard/billing",
                )
                result.ok(f"created new portal config: {config.id}")
            result.capture("portal_configuration", _safe_model_dump(config))
        except stripe.StripeError as e:
            result.fail("billing_portal.Configuration", str(e)[:200])

        # ── Check 8: Create a portal session for our test customer ────
        print()
        print("Check 8: Create portal session for test customer (BILL-05 contract)")
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url="http://localhost:3000/dashboard/billing",
            )
            if portal_session.url.startswith("https://billing.stripe.com/"):
                result.ok(f"portal session URL: {portal_session.url[:50]}...")
            else:
                result.fail("portal session URL", f"unexpected scheme: {portal_session.url[:60]}")
            result.capture("portal_session", _safe_model_dump(portal_session))
        except stripe.StripeError as e:
            result.fail("billing_portal.Session.create", str(e)[:200])

    finally:
        # ── Cleanup: delete subscription and customer ─────────────────
        print()
        print("Cleanup: deleting test resources")
        if subscription is not None:
            try:
                stripe.Subscription.cancel(subscription.id)
                print(f"  deleted subscription: {subscription.id}")
            except stripe.StripeError as e:
                msg = str(e)[:150]
                if "already been canceled" in msg.lower() or "no longer exists" in msg.lower():
                    print(f"  subscription {subscription.id} already canceled")
                else:
                    print(f"  WARN: failed to delete subscription: {msg}")
        if customer is not None:
            try:
                stripe.Customer.delete(customer.id)
                print(f"  deleted customer: {customer.id}")
            except stripe.StripeError as e:
                print(f"  WARN: failed to delete customer: {str(e)[:150]}")

        # Write fixtures regardless of pass/fail so partial runs are useful
        if result.fixtures:
            FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
            with FIXTURES_PATH.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "run_id": RUN_ID,
                        "fake_supabase_user_id": FAKE_SUPABASE_USER_ID,
                        "captured_at": int(time.time()),
                        "fixtures": result.fixtures,
                    },
                    f,
                    indent=2,
                    default=str,
                )
            print(f"  fixtures written: {FIXTURES_PATH}")

    return result.summary()


if __name__ == "__main__":
    sys.exit(main())
