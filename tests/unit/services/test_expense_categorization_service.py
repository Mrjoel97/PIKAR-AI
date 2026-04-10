# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ExpenseCategorizationService.

Tests cover:
- Keyword-based categorization for each category
- Transaction type overrides (payout -> transfers, revenue -> revenue, fee -> taxes_fees)
- Unknown descriptions default to "other"
- categorize_batch processes records and updates DB
- categorize_single convenience wrapper
"""

from __future__ import annotations

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


@pytest.fixture()
def categorizer():
    """Return an ExpenseCategorizationService instance."""
    from app.services.expense_categorization_service import (
        ExpenseCategorizationService,
    )

    return ExpenseCategorizationService()


# ---------------------------------------------------------------------------
# Transaction Type Override Tests
# ---------------------------------------------------------------------------


class TestTransactionTypeOverrides:
    """Verify that transaction_type takes priority over keyword matching."""

    def test_payout_categorized_as_transfers(self, categorizer):
        """Payout transaction_type always maps to 'transfers'."""
        result = categorizer.categorize_transaction(
            description="Some random payout description",
            transaction_type="payout",
        )
        assert result == "transfers"

    def test_revenue_categorized_as_revenue(self, categorizer):
        """Revenue transaction_type always maps to 'revenue'."""
        result = categorizer.categorize_transaction(
            description="Google Ads charge",
            transaction_type="revenue",
        )
        assert result == "revenue"

    def test_fee_categorized_as_taxes_fees(self, categorizer):
        """Fee transaction_type always maps to 'taxes_fees'."""
        result = categorizer.categorize_transaction(
            description="Some charge",
            transaction_type="fee",
        )
        assert result == "taxes_fees"


# ---------------------------------------------------------------------------
# Keyword Categorization Tests
# ---------------------------------------------------------------------------


class TestKeywordCategorization:
    """Verify keyword-based categorization for each category."""

    def test_stripe_fee_description_categorized_as_taxes_fees(self, categorizer):
        """'Stripe fee' in description maps to taxes_fees."""
        result = categorizer.categorize_transaction(
            description="Stripe fee",
            transaction_type="expense",
        )
        assert result == "taxes_fees"

    def test_google_ads_categorized_as_marketing(self, categorizer):
        """'Google Ads' in description maps to marketing."""
        result = categorizer.categorize_transaction(
            description="Google Ads campaign spend",
            transaction_type="expense",
        )
        assert result == "marketing"

    def test_facebook_ads_categorized_as_marketing(self, categorizer):
        """'Facebook Ads' in description maps to marketing."""
        result = categorizer.categorize_transaction(
            description="Facebook Ads monthly",
            transaction_type="expense",
        )
        assert result == "marketing"

    def test_slack_categorized_as_saas_tools(self, categorizer):
        """'Slack' in description maps to saas_tools."""
        result = categorizer.categorize_transaction(
            description="Slack Technologies Inc",
            transaction_type="expense",
        )
        assert result == "saas_tools"

    def test_notion_categorized_as_saas_tools(self, categorizer):
        """'Notion' in description maps to saas_tools."""
        result = categorizer.categorize_transaction(
            description="Notion Labs subscription",
            transaction_type="expense",
        )
        assert result == "saas_tools"

    def test_github_categorized_as_saas_tools(self, categorizer):
        """'GitHub' in description maps to saas_tools."""
        result = categorizer.categorize_transaction(
            description="GitHub Team plan",
            transaction_type="expense",
        )
        assert result == "saas_tools"

    def test_vercel_categorized_as_saas_tools(self, categorizer):
        """'Vercel' in description maps to saas_tools."""
        result = categorizer.categorize_transaction(
            description="Vercel Pro plan",
            transaction_type="expense",
        )
        assert result == "saas_tools"

    def test_payroll_categorized_as_payroll(self, categorizer):
        """'Payroll' in description maps to payroll."""
        result = categorizer.categorize_transaction(
            description="Payroll run March 2026",
            transaction_type="expense",
        )
        assert result == "payroll"

    def test_gusto_categorized_as_payroll(self, categorizer):
        """'Gusto' in description maps to payroll."""
        result = categorizer.categorize_transaction(
            description="Gusto payroll processing",
            transaction_type="expense",
        )
        assert result == "payroll"

    def test_aws_categorized_as_infrastructure(self, categorizer):
        """'AWS' in description maps to infrastructure."""
        result = categorizer.categorize_transaction(
            description="AWS monthly bill",
            transaction_type="expense",
        )
        assert result == "infrastructure"

    def test_gcp_categorized_as_infrastructure(self, categorizer):
        """'GCP' in description maps to infrastructure."""
        result = categorizer.categorize_transaction(
            description="GCP compute engine",
            transaction_type="expense",
        )
        assert result == "infrastructure"

    def test_heroku_categorized_as_infrastructure(self, categorizer):
        """'Heroku' in description maps to infrastructure."""
        result = categorizer.categorize_transaction(
            description="Heroku dyno hours",
            transaction_type="expense",
        )
        assert result == "infrastructure"

    def test_legal_categorized_as_professional_services(self, categorizer):
        """'Legal' in description maps to professional_services."""
        result = categorizer.categorize_transaction(
            description="Legal counsel retainer",
            transaction_type="expense",
        )
        assert result == "professional_services"

    def test_office_categorized_as_office(self, categorizer):
        """'Office' in description maps to office."""
        result = categorizer.categorize_transaction(
            description="Office supplies from Staples",
            transaction_type="expense",
        )
        assert result == "office"

    def test_airline_categorized_as_travel(self, categorizer):
        """'Airline' in description maps to travel."""
        result = categorizer.categorize_transaction(
            description="Airline ticket SFO-NYC",
            transaction_type="expense",
        )
        assert result == "travel"

    def test_manufacturing_categorized_as_cogs(self, categorizer):
        """'Manufacturing' in description maps to cogs."""
        result = categorizer.categorize_transaction(
            description="Manufacturing run batch 42",
            transaction_type="expense",
        )
        assert result == "cogs"

    def test_unknown_description_categorized_as_other(self, categorizer):
        """Unknown descriptions default to 'other'."""
        result = categorizer.categorize_transaction(
            description="Some completely random charge",
            transaction_type="expense",
        )
        assert result == "other"

    def test_case_insensitive_matching(self, categorizer):
        """Keyword matching is case-insensitive."""
        result = categorizer.categorize_transaction(
            description="GOOGLE ADS Campaign",
            transaction_type="expense",
        )
        assert result == "marketing"


# ---------------------------------------------------------------------------
# Metadata Fallback Tests
# ---------------------------------------------------------------------------


class TestMetadataFallback:
    """Verify metadata-based categorization fallback."""

    def test_metadata_stripe_fee_categorized_as_taxes_fees(self, categorizer):
        """When metadata has stripe_type='stripe_fee', categorize as taxes_fees."""
        result = categorizer.categorize_transaction(
            description="Unknown charge",
            transaction_type="adjustment",
            metadata={"stripe_type": "stripe_fee"},
        )
        assert result == "taxes_fees"


# ---------------------------------------------------------------------------
# Batch Categorization Tests
# ---------------------------------------------------------------------------


class TestCategorizeBatch:
    """Verify categorize_batch processes records and updates DB."""

    @pytest.mark.asyncio()
    async def test_categorize_batch_processes_records(self, categorizer):
        """categorize_batch queries uncategorized records and updates them."""
        mock_records = MagicMock()
        mock_records.data = [
            {
                "id": "rec-1",
                "description": "Google Ads spend",
                "transaction_type": "expense",
                "metadata": {},
            },
            {
                "id": "rec-2",
                "description": "Stripe payout",
                "transaction_type": "payout",
                "metadata": {},
            },
            {
                "id": "rec-3",
                "description": "Unknown vendor charge",
                "transaction_type": "expense",
                "metadata": {},
            },
        ]

        mock_update_result = MagicMock()
        mock_update_result.data = [{"id": "rec-1"}]

        mock_admin_cls = MagicMock()
        mock_client = MagicMock()
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.is_.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.update.return_value = mock_chain
        mock_client.table.return_value = mock_chain
        mock_admin_cls.return_value.client = mock_client

        mock_exec = AsyncMock()
        # First call: SELECT uncategorized records
        # Subsequent calls: UPDATE each record
        mock_exec.side_effect = [mock_records] + [mock_update_result] * 3

        # Patch the lazy imports at their source modules
        import app.services.base_service as bs_mod
        import app.services.supabase_async as sa_mod

        original_admin = getattr(bs_mod, "AdminService", None)
        original_exec = getattr(sa_mod, "execute_async", None)
        try:
            bs_mod.AdminService = mock_admin_cls
            sa_mod.execute_async = mock_exec
            result = await categorizer.categorize_batch("user-1", limit=500)
        finally:
            if original_admin is not None:
                bs_mod.AdminService = original_admin
            if original_exec is not None:
                sa_mod.execute_async = original_exec

        assert result["categorized"] == 3
        assert result["skipped"] == 0

    @pytest.mark.asyncio()
    async def test_categorize_batch_returns_zero_when_no_records(self, categorizer):
        """categorize_batch returns 0/0 when no uncategorized records exist."""
        mock_empty = MagicMock()
        mock_empty.data = []

        mock_client = MagicMock()
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.is_.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_client.table.return_value = mock_chain

        with (
            patch(
                "app.services.base_service.AdminService.client",
                new_callable=lambda: property(lambda self: mock_client),
            ),
            patch(
                "app.services.supabase_async.execute_async",
                new_callable=AsyncMock,
                return_value=mock_empty,
            ),
        ):
            result = await categorizer.categorize_batch("user-1")

        assert result["categorized"] == 0
        assert result["skipped"] == 0


# ---------------------------------------------------------------------------
# Single Categorization Convenience Wrapper Test
# ---------------------------------------------------------------------------


class TestCategorizeSingle:
    """Verify categorize_single convenience wrapper."""

    @pytest.mark.asyncio()
    async def test_categorize_single_returns_category(self, categorizer):
        """categorize_single returns the category for a single record."""
        record = {
            "description": "Vercel Pro plan",
            "transaction_type": "expense",
            "metadata": {},
        }
        result = await categorizer.categorize_single(record)
        assert result == "saas_tools"
