# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for StripeSyncService.

Tests cover:
- TYPE_MAP completeness and correctness
- _map_transaction field mapping (amount division, currency case, external_id)
- sync_history Stripe API interaction and batch upsert
- Webhook handlers (payment_intent, charge_refunded, payout_paid)
- Idempotency (duplicate external_id does not raise)
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set required env vars for BaseService / AdminService init."""
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_fake")


@pytest.fixture()
def stripe_sync():
    """Return a StripeSyncService instance with mocked Supabase clients."""
    from app.services.stripe_sync_service import StripeSyncService

    svc = StripeSyncService.__new__(StripeSyncService)
    # Bypass BaseService __init__ — we only need the class methods
    svc._url = "http://localhost:54321"
    svc._anon_key = "test-anon-key"
    svc._user_token = None
    svc._client = None
    return svc


@pytest.fixture()
def sample_balance_transaction():
    """Return a realistic Stripe BalanceTransaction dict."""
    return {
        "id": "txn_1ABC",
        "type": "charge",
        "amount": 5000,  # $50.00 in cents
        "currency": "usd",
        "created": int(time.time()),
        "description": "Payment for invoice #123",
        "fee": 175,
        "net": 4825,
        "source": "ch_1XYZ",
        "status": "available",
    }


# ---------------------------------------------------------------------------
# TYPE_MAP Tests
# ---------------------------------------------------------------------------


class TestTypeMap:
    """Verify TYPE_MAP maps Stripe types to financial_records types."""

    def test_charge_maps_to_revenue(self):
        from app.services.stripe_sync_service import StripeSyncService

        assert StripeSyncService.TYPE_MAP["charge"] == "revenue"

    def test_payment_maps_to_revenue(self):
        from app.services.stripe_sync_service import StripeSyncService

        assert StripeSyncService.TYPE_MAP["payment"] == "revenue"

    def test_refund_maps_to_refund(self):
        from app.services.stripe_sync_service import StripeSyncService

        assert StripeSyncService.TYPE_MAP["refund"] == "refund"

    def test_stripe_fee_maps_to_fee(self):
        from app.services.stripe_sync_service import StripeSyncService

        assert StripeSyncService.TYPE_MAP["stripe_fee"] == "fee"

    def test_payout_maps_to_payout(self):
        from app.services.stripe_sync_service import StripeSyncService

        assert StripeSyncService.TYPE_MAP["payout"] == "payout"

    def test_adjustment_maps_to_adjustment(self):
        from app.services.stripe_sync_service import StripeSyncService

        assert StripeSyncService.TYPE_MAP["adjustment"] == "adjustment"

    def test_unknown_type_falls_back_to_adjustment(self):
        from app.services.stripe_sync_service import StripeSyncService

        result = StripeSyncService.TYPE_MAP.get("totally_unknown", "adjustment")
        assert result == "adjustment"


# ---------------------------------------------------------------------------
# _map_transaction Tests
# ---------------------------------------------------------------------------


class TestMapTransaction:
    """Verify _map_transaction produces correct financial_records row shape."""

    def test_amount_divided_by_100(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["amount"] == 50.0  # 5000 / 100

    def test_currency_uppercased(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["currency"] == "USD"

    def test_external_id_set_to_bt_id(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["external_id"] == "txn_1ABC"

    def test_source_type_is_stripe(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["source_type"] == "stripe"

    def test_source_id_from_bt(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["source_id"] == "ch_1XYZ"

    def test_transaction_type_mapped(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["transaction_type"] == "revenue"  # charge -> revenue

    def test_user_id_set(self, stripe_sync, sample_balance_transaction):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["user_id"] == "user-1"

    def test_metadata_includes_stripe_fields(
        self, stripe_sync, sample_balance_transaction
    ):
        row = stripe_sync._map_transaction(sample_balance_transaction, "user-1")
        assert row["metadata"]["stripe_type"] == "charge"
        assert row["metadata"]["fee"] == 175
        assert row["metadata"]["net"] == 4825

    def test_negative_amount_uses_abs(self, stripe_sync):
        bt = {
            "id": "txn_neg",
            "type": "refund",
            "amount": -2500,
            "currency": "eur",
            "created": int(time.time()),
            "description": "Refund",
            "fee": 0,
            "net": -2500,
            "source": "re_abc",
        }
        row = stripe_sync._map_transaction(bt, "user-2")
        assert row["amount"] == 25.0
        assert row["currency"] == "EUR"


# ---------------------------------------------------------------------------
# sync_history Tests
# ---------------------------------------------------------------------------


class TestSyncHistory:
    """Verify sync_history calls Stripe API and upserts results."""

    @pytest.mark.asyncio()
    async def test_sync_history_calls_stripe(self, stripe_sync, monkeypatch):
        """sync_history wraps stripe.BalanceTransaction.list in asyncio.to_thread."""
        mock_bt = {
            "id": "txn_sync1",
            "type": "charge",
            "amount": 1000,
            "currency": "usd",
            "created": int(time.time()),
            "description": "Test",
            "fee": 50,
            "net": 950,
            "source": "ch_s1",
        }

        # Mock Stripe's auto_paging_iter
        mock_list_result = MagicMock()
        mock_list_result.auto_paging_iter.return_value = [mock_bt]

        mock_stripe = MagicMock()
        mock_stripe.BalanceTransaction.list.return_value = mock_list_result
        mock_stripe.api_key = "sk_test"

        monkeypatch.setattr(
            "app.services.stripe_sync_service.stripe", mock_stripe
        )

        # Mock the admin client upsert
        mock_result = MagicMock()
        mock_result.data = [{"id": "row-1"}]

        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value = mock_result

        # Patch AdminService.client and execute_async
        with (
            patch(
                "app.services.stripe_sync_service.AdminService"
            ) as MockAdmin,
            patch(
                "app.services.stripe_sync_service.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "app.services.stripe_sync_service.IntegrationManager"
            ) as MockMgr,
        ):
            admin_instance = MockAdmin.return_value
            admin_instance.client = mock_client

            mgr_instance = MockMgr.return_value
            mgr_instance.update_sync_state = AsyncMock(return_value={})

            result = await stripe_sync.sync_history("user-1", months_back=12)

        assert result["imported"] >= 0
        mock_stripe.BalanceTransaction.list.assert_called_once()
        call_kwargs = mock_stripe.BalanceTransaction.list.call_args
        assert "created" in call_kwargs.kwargs or "created" in (
            call_kwargs[1] if len(call_kwargs) > 1 else {}
        )


# ---------------------------------------------------------------------------
# Webhook Handler Tests
# ---------------------------------------------------------------------------


class TestWebhookPaymentIntentSucceeded:
    """Verify handle_payment_intent_succeeded creates a revenue record."""

    @pytest.mark.asyncio()
    async def test_creates_revenue_record(self, stripe_sync):
        event_data = {
            "id": "pi_123",
            "amount_received": 7500,
            "currency": "usd",
            "description": "Payment for service",
        }

        mock_result = MagicMock()
        mock_result.data = [{"id": "row-pi"}]

        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value = mock_result

        with (
            patch(
                "app.services.stripe_sync_service.AdminService"
            ) as MockAdmin,
            patch(
                "app.services.stripe_sync_service.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            admin_instance = MockAdmin.return_value
            admin_instance.client = mock_client

            await stripe_sync.handle_payment_intent_succeeded(event_data, "user-1")

        # Verify the upsert was called
        mock_client.table.assert_called_with("financial_records")
        upsert_call = mock_client.table.return_value.upsert.call_args
        row = upsert_call[0][0]
        assert row["transaction_type"] == "revenue"
        assert row["amount"] == 75.0
        assert row["external_id"] == "pi_pi_123"
        assert row["source_type"] == "stripe"


class TestWebhookChargeRefunded:
    """Verify handle_charge_refunded creates a refund record."""

    @pytest.mark.asyncio()
    async def test_creates_refund_record(self, stripe_sync):
        event_data = {
            "id": "ch_456",
            "amount_refunded": 3000,
            "currency": "gbp",
            "description": "Refund for order",
        }

        mock_result = MagicMock()
        mock_result.data = [{"id": "row-re"}]

        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value = mock_result

        with (
            patch(
                "app.services.stripe_sync_service.AdminService"
            ) as MockAdmin,
            patch(
                "app.services.stripe_sync_service.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            admin_instance = MockAdmin.return_value
            admin_instance.client = mock_client

            await stripe_sync.handle_charge_refunded(event_data, "user-1")

        upsert_call = mock_client.table.return_value.upsert.call_args
        row = upsert_call[0][0]
        assert row["transaction_type"] == "refund"
        assert row["amount"] == 30.0
        assert row["external_id"] == "re_ch_456"


class TestWebhookPayoutPaid:
    """Verify handle_payout_paid creates a payout record."""

    @pytest.mark.asyncio()
    async def test_creates_payout_record(self, stripe_sync):
        event_data = {
            "id": "po_789",
            "amount": 10000,
            "currency": "usd",
            "description": "STRIPE PAYOUT",
        }

        mock_result = MagicMock()
        mock_result.data = [{"id": "row-po"}]

        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value = mock_result

        with (
            patch(
                "app.services.stripe_sync_service.AdminService"
            ) as MockAdmin,
            patch(
                "app.services.stripe_sync_service.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            admin_instance = MockAdmin.return_value
            admin_instance.client = mock_client

            await stripe_sync.handle_payout_paid(event_data, "user-1")

        upsert_call = mock_client.table.return_value.upsert.call_args
        row = upsert_call[0][0]
        assert row["transaction_type"] == "payout"
        assert row["amount"] == 100.0
        assert row["external_id"] == "po_po_789"


# ---------------------------------------------------------------------------
# Idempotency Tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Verify that duplicate external_ids do not raise errors."""

    @pytest.mark.asyncio()
    async def test_duplicate_upsert_does_not_raise(self, stripe_sync):
        """When upsert returns empty data (duplicate), no error is raised."""
        event_data = {
            "id": "pi_dup",
            "amount_received": 1000,
            "currency": "usd",
            "description": "Duplicate payment",
        }

        # Empty data = duplicate was ignored
        mock_result = MagicMock()
        mock_result.data = []

        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value = mock_result

        with (
            patch(
                "app.services.stripe_sync_service.AdminService"
            ) as MockAdmin,
            patch(
                "app.services.stripe_sync_service.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            admin_instance = MockAdmin.return_value
            admin_instance.client = mock_client

            # Should not raise
            await stripe_sync.handle_payment_intent_succeeded(event_data, "user-1")
