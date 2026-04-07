"""Stripe CLI end-to-end UAT helper — Plan 50-04.

This is an OPERATOR AID, not a CI test. It drives a scripted Stripe CLI
webhook-trigger sequence against a locally-running Pikar-AI dev stack and
asserts that the `subscriptions` and `stripe_webhook_events` tables end up in
the expected state after each step.

It re-validates the end-to-end billing flow shipped across Phase 50:

    * 50-01 — hardened webhook handler (BILL-01 event-ordering fix +
      BILL-02 idempotency via stripe_webhook_events ledger)
    * 50-02 — SubscriptionBadge + realtime subscription channel
    * 50-03 — BillingMetricsService (DB-native MRR)
    * 50-04 — SubscriptionBadge placement + portal unit test + this helper

PREREQUISITES (all must be satisfied before running):
    * Stripe CLI installed and `stripe login` completed
    * Local stack running:
        - `supabase start`
        - `docker compose up` (backend + redis)
        - `cd frontend && npm run dev`
    * `stripe listen --forward-to http://localhost:3000/api/webhooks/stripe`
      running in a separate terminal, with its whsec_... copied into
      frontend/.env.local as STRIPE_WEBHOOK_SECRET (then restart the dev
      server so it picks up the new value)
    * TEST_USER_ID env var set to a real Supabase user UUID in the local
      auth.users table
    * SUPABASE_DB_URL env var set to the local Postgres DSN (defaults to
      `postgresql://postgres:postgres@localhost:54322/postgres` which is
      the standard `supabase start` value)
    * STRIPE_CLI_ENABLED=1 env var to opt in — without it, the test is
      skipped so CI stays green

RUN WITH:
    STRIPE_CLI_ENABLED=1 TEST_USER_ID=<uuid> uv run pytest \\
        tests/e2e/test_stripe_checkout_flow.py -v -s

This test is SKIPPED in CI by default. It requires the Stripe CLI, live
local services, and a real Supabase user — none of which are available in
GitHub Actions or Cloud Build.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from collections.abc import Iterable

import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate: skip the entire module unless the operator explicitly opts in.
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("STRIPE_CLI_ENABLED"),
        reason=(
            "Stripe CLI e2e helper is opt-in. Set STRIPE_CLI_ENABLED=1 and "
            "TEST_USER_ID=<uuid> and follow the prerequisites in the module "
            "docstring to run it locally."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Constants / config
# ---------------------------------------------------------------------------

DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:54322/postgres"
POLL_INTERVAL_SECONDS = 0.5
DEFAULT_POLL_TIMEOUT_SECONDS = 10


def _require_env(name: str) -> str:
    """Return the value of a required env var or skip the test with a hint."""
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"Missing required env var {name}. See module docstring for setup.")
    return value


def _require_stripe_cli() -> str:
    """Return the absolute path to the `stripe` CLI or skip the test."""
    path = shutil.which("stripe")
    if not path:
        pytest.skip(
            "Stripe CLI not found on PATH. Install from "
            "https://stripe.com/docs/stripe-cli and run `stripe login`."
        )
    return path


def _run_stripe(cli: str, args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """Execute a `stripe` CLI invocation and return the completed process.

    Raises AssertionError with the captured stderr if the CLI exits non-zero,
    so failing triggers surface clearly in test output.
    """
    argv = [cli, *args]
    logger.info("running stripe CLI: %s", " ".join(argv))
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, (
        f"stripe CLI failed (exit {proc.returncode}):\n"
        f"STDOUT:\n{proc.stdout}\n"
        f"STDERR:\n{proc.stderr}"
    )
    return proc


def _db_query(db_url: str, sql: str) -> str:
    """Run a psql query and return stdout (tab-separated, no header)."""
    argv = [
        "psql",
        db_url,
        "-At",  # unaligned + tuples-only so output is machine-readable
        "-c",
        sql,
    ]
    if not shutil.which("psql"):
        pytest.skip(
            "psql not found on PATH. Install the PostgreSQL client tools "
            "(or set PATH to include your Supabase CLI-bundled psql)."
        )
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, (
        f"psql failed (exit {proc.returncode}):\n"
        f"SQL: {sql}\n"
        f"STDOUT:\n{proc.stdout}\n"
        f"STDERR:\n{proc.stderr}"
    )
    return proc.stdout.strip()


# ---------------------------------------------------------------------------
# Helpers — table assertions and polling
# ---------------------------------------------------------------------------


def _clear_test_rows(db_url: str, user_id: str) -> None:
    """Delete prior test rows from both tables so the run is idempotent.

    This is scoped to the specific TEST_USER_ID; it does NOT drop tables and
    does NOT touch rows belonging to other users on the same local DB.
    """
    _db_query(
        db_url,
        f"DELETE FROM public.subscriptions WHERE user_id = '{user_id}';",
    )
    # Clear any prior ledger rows emitted during a previous run of this test.
    # We match on the canonical Stripe test-mode event IDs that `stripe
    # trigger` produces, which include the customer's metadata supabase
    # user_id. Since stripe_webhook_events has no direct user_id column, we
    # wipe every row whose event_id matches the trigger pattern — safe in a
    # local dev DB.
    _db_query(
        db_url,
        (
            "DELETE FROM public.stripe_webhook_events "
            "WHERE type IN ("
            "'checkout.session.completed',"
            "'customer.subscription.created',"
            "'customer.subscription.updated',"
            "'customer.subscription.deleted'"
            ");"
        ),
    )


def _poll_subscription(
    db_url: str,
    user_id: str,
    *,
    expected_active: bool,
    timeout: int = DEFAULT_POLL_TIMEOUT_SECONDS,
) -> dict[str, str]:
    """Poll public.subscriptions until is_active matches expected_active.

    Returns a dict of the matched row fields on success, or raises
    AssertionError with a helpful timeout message on failure.
    """
    deadline = time.monotonic() + timeout
    last_snapshot: str = "(no row)"
    while time.monotonic() < deadline:
        output = _db_query(
            db_url,
            (
                "SELECT is_active, tier, will_renew, last_event_type "
                f"FROM public.subscriptions WHERE user_id = '{user_id}';"
            ),
        )
        last_snapshot = output or "(no row)"
        if output:
            is_active, tier, will_renew, last_event_type = output.split("|")
            row = {
                "is_active": is_active,
                "tier": tier,
                "will_renew": will_renew,
                "last_event_type": last_event_type,
            }
            if (is_active == "t") == expected_active:
                return row
        time.sleep(POLL_INTERVAL_SECONDS)

    raise AssertionError(
        f"subscriptions row for user_id={user_id} did not reach "
        f"is_active={expected_active} within {timeout}s. "
        f"Last observed: {last_snapshot}"
    )


def _assert_webhook_event_processed(
    db_url: str,
    event_type: str,
    *,
    timeout: int = DEFAULT_POLL_TIMEOUT_SECONDS,
) -> None:
    """Assert that at least one processed webhook row exists for a given type.

    The handler writes to stripe_webhook_events with status='processed' after
    successfully handling an event — this confirms the full pipeline ran.
    """
    deadline = time.monotonic() + timeout
    last_count: str = "(not queried)"
    while time.monotonic() < deadline:
        count = _db_query(
            db_url,
            (
                "SELECT COUNT(*) FROM public.stripe_webhook_events "
                f"WHERE type = '{event_type}' AND status = 'processed';"
            ),
        )
        last_count = count
        if count and int(count) >= 1:
            return
        time.sleep(POLL_INTERVAL_SECONDS)

    raise AssertionError(
        f"no stripe_webhook_events row with type={event_type!r} and "
        f"status='processed' within {timeout}s. Last count: {last_count}"
    )


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------


def test_stripe_checkout_flow_creates_and_clears_subscription() -> None:
    """Drive a full checkout-then-cancel Stripe CLI sequence and verify state.

    Steps:
        1. Clear any prior test rows for TEST_USER_ID.
        2. Trigger checkout.session.completed — assert subscription row
           appears with is_active=true and a processed webhook ledger row.
        3. Trigger customer.subscription.deleted — assert subscription row
           flips to is_active=false and a second processed webhook ledger
           row appears.
    """
    stripe_cli = _require_stripe_cli()
    test_user_id = _require_env("TEST_USER_ID")
    db_url = os.environ.get("SUPABASE_DB_URL", DEFAULT_DB_URL)

    logger.info("Using DB URL: %s", db_url)
    logger.info("Using TEST_USER_ID: %s", test_user_id)

    # ── Setup: wipe prior test rows so the run is re-runnable ──────────
    _clear_test_rows(db_url, test_user_id)

    # ── Step 1: trigger checkout.session.completed ─────────────────────
    _run_stripe(
        stripe_cli,
        [
            "trigger",
            "checkout.session.completed",
            "--add",
            f"checkout_session:metadata.supabase_user_id={test_user_id}",
        ],
    )

    # After the ordered customer.subscription.created that Stripe delivers
    # alongside checkout.session.completed lands, the row should exist and
    # be active. The source of truth for tier/is_active/will_renew is now
    # customer.subscription.created (see Plan 50-01 BILL-01 fix), so
    # last_event_type should be 'customer.subscription.created' — NOT
    # 'checkout.session.completed'.
    active_row = _poll_subscription(
        db_url,
        test_user_id,
        expected_active=True,
        timeout=DEFAULT_POLL_TIMEOUT_SECONDS,
    )
    assert active_row["is_active"] == "t", (
        f"Expected is_active=t after checkout, got {active_row}"
    )
    assert active_row["last_event_type"] == "customer.subscription.created", (
        "BILL-01 regression: expected last_event_type="
        "customer.subscription.created (the demoted checkout.session.completed "
        f"handler must NOT be the last writer). Got {active_row}"
    )
    _assert_webhook_event_processed(db_url, "checkout.session.completed")
    _assert_webhook_event_processed(db_url, "customer.subscription.created")

    # ── Step 2: trigger customer.subscription.deleted ──────────────────
    _run_stripe(
        stripe_cli,
        [
            "trigger",
            "customer.subscription.deleted",
            "--add",
            f"subscription:metadata.supabase_user_id={test_user_id}",
        ],
    )

    canceled_row = _poll_subscription(
        db_url,
        test_user_id,
        expected_active=False,
        timeout=DEFAULT_POLL_TIMEOUT_SECONDS,
    )
    assert canceled_row["is_active"] == "f", (
        f"Expected is_active=f after delete, got {canceled_row}"
    )
    _assert_webhook_event_processed(db_url, "customer.subscription.deleted")
