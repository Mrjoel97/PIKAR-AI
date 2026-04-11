# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for EmailABTestingService.

Covers A/B variant creation, metric tracking, winner selection based on
open/click rates, and applying the winning variant.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure BaseService can initialize without real Supabase credentials
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
SEQUENCE_ID = "seq-00000000-0000-0000-0000-000000000001"
STEP_A_ID = "step-a-0000-0000-0000-000000000001"
STEP_B_ID = "step-b-0000-0000-0000-000000000002"
ENROLL_A_ID = "enr-a-0000-0000-0000-000000000001"
ENROLL_B_ID = "enr-b-0000-0000-0000-000000000002"


def _make_original_step(
    step_id: str = STEP_A_ID,
    step_number: int = 0,
    subject: str = "Original Subject",
    body: str = "Original Body",
) -> dict:
    """Return a canonical email_sequence_steps row."""
    return {
        "id": step_id,
        "sequence_id": SEQUENCE_ID,
        "step_number": step_number,
        "subject_template": subject,
        "body_template": body,
        "delay_hours": 24,
        "delay_type": "after_previous",
        "metadata": {},
    }


def _make_variant_step(
    step_id: str,
    ab_test_id: str,
    label: str,
    subject: str,
    body: str,
    step_number: int = 0,
    split_pct: int = 50,
) -> dict:
    return {
        "id": step_id,
        "sequence_id": SEQUENCE_ID,
        "step_number": step_number,
        "subject_template": subject,
        "body_template": body,
        "delay_hours": 24,
        "delay_type": "after_previous",
        "metadata": {
            "ab_test_id": ab_test_id,
            "is_variant": True,
            "variant_label": label,
            "split_pct": split_pct,
        },
    }


def _make_tracking_events(
    sends_a: int = 0,
    opens_a: int = 0,
    clicks_a: int = 0,
    sends_b: int = 0,
    opens_b: int = 0,
    clicks_b: int = 0,
) -> tuple[list, list, list]:
    """Build fake tracking event rows for both variants.

    Returns three buckets (delivered, opens, clicks) keyed by enrollment_id.
    """
    delivered = (
        [{"enrollment_id": ENROLL_A_ID, "event_type": "delivered"}] * sends_a
        + [{"enrollment_id": ENROLL_B_ID, "event_type": "delivered"}] * sends_b
    )
    opens = (
        [{"enrollment_id": ENROLL_A_ID, "event_type": "open"}] * opens_a
        + [{"enrollment_id": ENROLL_B_ID, "event_type": "open"}] * opens_b
    )
    clicks = (
        [{"enrollment_id": ENROLL_A_ID, "event_type": "click"}] * clicks_a
        + [{"enrollment_id": ENROLL_B_ID, "event_type": "click"}] * clicks_b
    )
    return delivered, opens, clicks


class _FakeSupabase:
    """Minimal fake supabase-py chainable client for AB testing tests.

    Supports table(...).select/update/insert/delete + eq/order/in_/limit.
    Records inserts for assertions. Dispatches responses via a router map.
    """

    def __init__(self, router: dict):
        self._router = router
        self.inserts: list[tuple[str, list[dict] | dict]] = []
        self.updates: list[tuple[str, dict, dict]] = []
        self.deletes: list[tuple[str, dict]] = []

    def table(self, name: str):  # noqa: D401
        return _FakeTable(name, self)


class _FakeTable:
    def __init__(self, name: str, client: _FakeSupabase):
        self._name = name
        self._client = client
        self._op = None
        self._payload = None
        self._filters: dict = {}
        self._in_filters: dict = {}
        self._order = None
        self._limit = None

    # --- SQL ops ---
    def select(self, *args, **kwargs):
        self._op = "select"
        return self

    def insert(self, rows):
        self._op = "insert"
        self._payload = rows
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def delete(self):
        self._op = "delete"
        return self

    # --- filters ---
    def eq(self, col, val):
        self._filters[col] = val
        return self

    def in_(self, col, vals):
        self._in_filters[col] = list(vals)
        return self

    def order(self, col, desc: bool = False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    # --- execution (when the query is awaited via execute_async) ---
    def _finalize(self):
        """Return a MagicMock-like response object with a ``data`` attr."""
        key = (self._name, self._op)
        router_entry = self._client._router.get(key)
        if self._op == "insert":
            self._client.inserts.append((self._name, self._payload))
            if callable(router_entry):
                data = router_entry(self._payload, self._filters)
            elif router_entry is not None:
                data = router_entry
            else:
                # Default: echo back the payload as a list of dicts with IDs
                if isinstance(self._payload, list):
                    data = [
                        {**r, "id": f"new-id-{i}"} for i, r in enumerate(self._payload)
                    ]
                else:
                    data = [{**self._payload, "id": "new-id-0"}]
            return _FakeResponse(data)

        if self._op == "update":
            self._client.updates.append(
                (self._name, dict(self._payload), dict(self._filters))
            )
            if callable(router_entry):
                data = router_entry(self._payload, self._filters)
            elif router_entry is not None:
                data = router_entry
            else:
                data = [dict(self._payload)]
            return _FakeResponse(data)

        if self._op == "delete":
            self._client.deletes.append((self._name, dict(self._filters)))
            if callable(router_entry):
                data = router_entry(self._filters)
            elif router_entry is not None:
                data = router_entry
            else:
                data = []
            return _FakeResponse(data)

        # select
        if callable(router_entry):
            data = router_entry(self._filters, self._in_filters)
        elif router_entry is not None:
            data = router_entry
        else:
            data = []
        return _FakeResponse(data)


class _FakeResponse:
    def __init__(self, data):
        self.data = data
        self.count = len(data) if isinstance(data, list) else None


async def _fake_execute_async(query, op_name: str = "", **kwargs):
    """Stand-in for supabase_async.execute_async used by the service."""
    return query._finalize()


# ---------------------------------------------------------------------------
# create_ab_test
# ---------------------------------------------------------------------------


class TestCreateABTest:
    """create_ab_test creates a Variant B step and links both variants via ab_test_id."""

    @pytest.mark.asyncio
    async def test_creates_variant_b_and_links_both(self):
        original_step = _make_original_step()

        router = {
            # select the sequence's steps for the given step_index
            ("email_sequence_steps", "select"): [original_step],
            # update original step -> tag it as Variant A
            ("email_sequence_steps", "update"): lambda payload, filters: [
                {**original_step, **payload}
            ],
            # insert the new variant B row
            ("email_sequence_steps", "insert"): lambda payload, filters: [
                {**(payload[0] if isinstance(payload, list) else payload), "id": STEP_B_ID}
            ],
        }
        fake_client = _FakeSupabase(router)

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.create_ab_test(
                user_id=USER_ID,
                sequence_id=SEQUENCE_ID,
                step_index=0,
                variant_b_subject="Variant B Subject",
                variant_b_body="Variant B Body",
                split_pct=50,
            )

        assert "ab_test_id" in result
        assert result["split_pct"] == 50
        assert result["variant_a"]["subject_template"] == "Original Subject"
        assert result["variant_b"]["subject_template"] == "Variant B Subject"

        # Both variants must share the same ab_test_id
        assert (
            result["variant_a"]["metadata"]["ab_test_id"]
            == result["variant_b"]["metadata"]["ab_test_id"]
        )
        assert result["variant_a"]["metadata"]["variant_label"] == "A"
        assert result["variant_b"]["metadata"]["variant_label"] == "B"

        # An insert and an update should have happened
        assert any(t[0] == "email_sequence_steps" for t in fake_client.inserts)
        assert any(t[0] == "email_sequence_steps" for t in fake_client.updates)

    @pytest.mark.asyncio
    async def test_raises_when_step_index_out_of_range(self):
        router = {
            ("email_sequence_steps", "select"): [],
        }
        fake_client = _FakeSupabase(router)

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            with pytest.raises(ValueError):
                await svc.create_ab_test(
                    user_id=USER_ID,
                    sequence_id=SEQUENCE_ID,
                    step_index=0,
                    variant_b_subject="x",
                    variant_b_body="y",
                )


# ---------------------------------------------------------------------------
# get_results
# ---------------------------------------------------------------------------


class TestGetResults:
    """get_results returns open_rate and click_rate per variant."""

    @pytest.mark.asyncio
    async def test_returns_rates_and_sample_sizes(self):
        ab_test_id = "ab-test-0000-0000-0000-000000000001"

        variant_a = _make_variant_step(
            STEP_A_ID, ab_test_id, "A", "Subject A", "Body A"
        )
        variant_b = _make_variant_step(
            STEP_B_ID, ab_test_id, "B", "Subject B", "Body B"
        )

        delivered_a = [
            {"enrollment_id": ENROLL_A_ID, "event_type": "delivered", "step_number": 0}
        ] * 100
        opens_a = [
            {"enrollment_id": ENROLL_A_ID, "event_type": "open", "step_number": 0}
        ] * 25
        clicks_a = [
            {"enrollment_id": ENROLL_A_ID, "event_type": "click", "step_number": 0}
        ] * 5

        delivered_b = [
            {"enrollment_id": ENROLL_B_ID, "event_type": "delivered", "step_number": 0}
        ] * 100
        opens_b = [
            {"enrollment_id": ENROLL_B_ID, "event_type": "open", "step_number": 0}
        ] * 35
        clicks_b = [
            {"enrollment_id": ENROLL_B_ID, "event_type": "click", "step_number": 0}
        ] * 10

        # Enrollments: link enrollment_id -> variant via step_number naming
        enrollments_a = [{"id": ENROLL_A_ID, "sequence_id": SEQUENCE_ID}]
        enrollments_b = [{"id": ENROLL_B_ID, "sequence_id": SEQUENCE_ID}]

        def _select_steps(filters, in_filters):
            return [variant_a, variant_b]

        def _select_events(filters, in_filters):
            # Service queries by enrollment_ids_in -> combined list
            ids = in_filters.get("enrollment_id") or []
            events = []
            if ENROLL_A_ID in ids:
                events += delivered_a + opens_a + clicks_a
            if ENROLL_B_ID in ids:
                events += delivered_b + opens_b + clicks_b
            return events

        def _select_enrollments(filters, in_filters):
            return enrollments_a + enrollments_b

        router = {
            ("email_sequence_steps", "select"): _select_steps,
            ("email_sequence_enrollments", "select"): _select_enrollments,
            ("email_tracking_events", "select"): _select_events,
        }
        fake_client = _FakeSupabase(router)

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.get_results(
                user_id=USER_ID, sequence_id=SEQUENCE_ID, ab_test_id=ab_test_id
            )

        assert "variant_a" in result
        assert "variant_b" in result
        assert result["variant_a"]["sends"] == 100
        assert result["variant_b"]["sends"] == 100
        assert result["variant_a"]["opens"] == 25
        assert result["variant_b"]["opens"] == 35
        assert result["variant_a"]["open_rate"] == pytest.approx(0.25)
        assert result["variant_b"]["open_rate"] == pytest.approx(0.35)
        assert result["variant_a"]["click_rate"] == pytest.approx(0.05)
        assert result["variant_b"]["click_rate"] == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# select_winner
# ---------------------------------------------------------------------------


def _build_winner_router(
    ab_test_id: str,
    sends_a: int,
    opens_a: int,
    clicks_a: int,
    sends_b: int,
    opens_b: int,
    clicks_b: int,
) -> _FakeSupabase:
    variant_a = _make_variant_step(
        STEP_A_ID, ab_test_id, "A", "Subject A", "Body A"
    )
    variant_b = _make_variant_step(
        STEP_B_ID, ab_test_id, "B", "Subject B", "Body B"
    )

    def _select_steps(filters, in_filters):
        return [variant_a, variant_b]

    def _select_enrollments(filters, in_filters):
        return [
            {"id": ENROLL_A_ID, "sequence_id": SEQUENCE_ID},
            {"id": ENROLL_B_ID, "sequence_id": SEQUENCE_ID},
        ]

    def _select_events(filters, in_filters):
        ids = in_filters.get("enrollment_id") or []
        events = []
        if ENROLL_A_ID in ids:
            events += [
                {"enrollment_id": ENROLL_A_ID, "event_type": "delivered"}
            ] * sends_a
            events += [
                {"enrollment_id": ENROLL_A_ID, "event_type": "open"}
            ] * opens_a
            events += [
                {"enrollment_id": ENROLL_A_ID, "event_type": "click"}
            ] * clicks_a
        if ENROLL_B_ID in ids:
            events += [
                {"enrollment_id": ENROLL_B_ID, "event_type": "delivered"}
            ] * sends_b
            events += [
                {"enrollment_id": ENROLL_B_ID, "event_type": "open"}
            ] * opens_b
            events += [
                {"enrollment_id": ENROLL_B_ID, "event_type": "click"}
            ] * clicks_b
        return events

    router = {
        ("email_sequence_steps", "select"): _select_steps,
        ("email_sequence_enrollments", "select"): _select_enrollments,
        ("email_tracking_events", "select"): _select_events,
        ("email_sequence_steps", "update"): lambda payload, filters: [
            {**variant_a, **payload}
        ],
    }
    return _FakeSupabase(router)


class TestSelectWinner:
    """select_winner scores variants and requires minimum sample size."""

    @pytest.mark.asyncio
    async def test_picks_higher_combined_score(self):
        ab_test_id = "ab-test-winner-B"
        # A: open 20%, click 5% -> score = 0.7*0.2 + 0.3*0.05 = 0.155
        # B: open 30%, click 10% -> score = 0.7*0.3 + 0.3*0.1 = 0.24
        fake_client = _build_winner_router(
            ab_test_id, 100, 20, 5, 100, 30, 10
        )

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.select_winner(
                user_id=USER_ID,
                sequence_id=SEQUENCE_ID,
                ab_test_id=ab_test_id,
                min_sample=50,
            )

        assert result["winner"] == "B"
        assert result["score_a"] == pytest.approx(0.155, rel=1e-3)
        assert result["score_b"] == pytest.approx(0.24, rel=1e-3)

    @pytest.mark.asyncio
    async def test_insufficient_data_below_min_sample(self):
        ab_test_id = "ab-test-insufficient"
        fake_client = _build_winner_router(
            ab_test_id, 10, 5, 1, 10, 6, 2
        )

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.select_winner(
                user_id=USER_ID,
                sequence_id=SEQUENCE_ID,
                ab_test_id=ab_test_id,
                min_sample=50,
            )

        assert result["winner"] == "insufficient_data"
        assert "50" in result["reason"]

    @pytest.mark.asyncio
    async def test_ties_default_to_variant_a(self):
        ab_test_id = "ab-test-tie"
        # Both variants have identical metrics -> score_a == score_b -> A wins
        fake_client = _build_winner_router(
            ab_test_id, 100, 25, 5, 100, 25, 5
        )

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.select_winner(
                user_id=USER_ID,
                sequence_id=SEQUENCE_ID,
                ab_test_id=ab_test_id,
                min_sample=50,
            )

        assert result["winner"] == "A"
        assert result["score_a"] == result["score_b"]


# ---------------------------------------------------------------------------
# apply_winner
# ---------------------------------------------------------------------------


class TestApplyWinner:
    """apply_winner replaces the original step with the winning variant's content."""

    @pytest.mark.asyncio
    async def test_replaces_original_with_winner_and_deactivates_loser(self):
        ab_test_id = "ab-test-apply"

        # B wins by a lot
        fake_client = _build_winner_router(
            ab_test_id, 100, 10, 2, 100, 50, 20
        )

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.apply_winner(
                user_id=USER_ID,
                sequence_id=SEQUENCE_ID,
                ab_test_id=ab_test_id,
            )

        assert result["winner"] == "B"
        assert result["applied"] is True

        # At least one update should have been issued to the steps table —
        # the winning variant's content replaces the step-A row.
        update_tables = [u[0] for u in fake_client.updates]
        assert "email_sequence_steps" in update_tables

    @pytest.mark.asyncio
    async def test_apply_winner_skips_when_insufficient_data(self):
        ab_test_id = "ab-test-apply-insuf"
        fake_client = _build_winner_router(
            ab_test_id, 5, 1, 0, 5, 2, 0
        )

        with patch(
            "app.services.email_ab_testing_service.AdminService"
        ) as MockAdmin, patch(
            "app.services.email_ab_testing_service.execute_async",
            new=AsyncMock(side_effect=_fake_execute_async),
        ):
            MockAdmin.return_value.client = fake_client

            from app.services.email_ab_testing_service import EmailABTestingService

            svc = EmailABTestingService()
            result = await svc.apply_winner(
                user_id=USER_ID,
                sequence_id=SEQUENCE_ID,
                ab_test_id=ab_test_id,
            )

        assert result["winner"] == "insufficient_data"
        assert result["applied"] is False
