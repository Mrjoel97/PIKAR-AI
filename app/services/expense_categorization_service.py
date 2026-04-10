# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ExpenseCategorizationService — Automatic Stripe expense categorization.

Provides rule-based + keyword categorization for Stripe transactions.
Categories include: marketing, saas_tools, cogs, payroll, office, travel,
professional_services, infrastructure, taxes_fees, transfers, revenue, other.

Categorization priority:
1. Transaction type overrides (payout -> transfers, revenue -> revenue, fee -> taxes_fees)
2. Description keyword matching (case-insensitive substring)
3. Metadata fallback (stripe_type == "stripe_fee" -> taxes_fees)
4. Default: "other"
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class ExpenseCategorizationService:
    """Categorize Stripe transactions into business expense categories.

    Uses a combination of transaction type overrides and keyword-based
    description matching to assign categories automatically.
    """

    #: Map category names to keyword patterns (case-insensitive substring match).
    KEYWORD_RULES: ClassVar[dict[str, list[str]]] = {
        "marketing": [
            "google ads",
            "facebook ads",
            "meta ads",
            "tiktok ads",
            "linkedin ads",
            "mailchimp",
            "sendgrid",
            "hubspot marketing",
            "semrush",
            "ahrefs",
        ],
        "saas_tools": [
            "slack",
            "notion",
            "github",
            "vercel",
            "figma",
            "canva",
            "zapier",
            "airtable",
            "jira",
            "confluence",
            "1password",
            "dropbox",
        ],
        "payroll": [
            "gusto",
            "payroll",
            "salary",
            "wages",
            "adp",
            "rippling",
        ],
        "infrastructure": [
            "aws",
            "amazon web services",
            "gcp",
            "google cloud",
            "heroku",
            "digitalocean",
            "cloudflare",
            "datadog",
            "sentry",
        ],
        "professional_services": [
            "legal",
            "accounting",
            "consulting",
            "lawyer",
            "attorney",
            "cpa",
            "bookkeeper",
        ],
        "office": [
            "office",
            "coworking",
            "wework",
            "rent",
            "utilities",
            "internet",
        ],
        "travel": [
            "airline",
            "hotel",
            "uber",
            "lyft",
            "airbnb",
            "flight",
        ],
        "taxes_fees": [
            "stripe fee",
            "tax",
            "irs",
            "state tax",
            "processing fee",
        ],
        "cogs": [
            "manufacturing",
            "materials",
            "shipping",
            "fulfillment",
            "warehouse",
        ],
        "transfers": [],  # Assigned by transaction_type, not keywords
    }

    def categorize_transaction(
        self,
        description: str,
        transaction_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Categorize a single transaction based on description and type.

        Priority order:
        1. Transaction type overrides (payout, revenue, fee)
        2. Keyword matching on description
        3. Metadata fallback (stripe_type)
        4. Default "other"

        Args:
            description: The transaction description text.
            transaction_type: The financial_records transaction_type value.
            metadata: Optional JSONB metadata dict from the record.

        Returns:
            Category name string (e.g., "marketing", "saas_tools", "other").
        """
        # 1. Transaction type overrides
        if transaction_type == "payout":
            return "transfers"
        if transaction_type == "revenue":
            return "revenue"
        if transaction_type == "fee":
            return "taxes_fees"

        # 2. Keyword matching (case-insensitive)
        desc_lower = description.lower()
        for category, keywords in self.KEYWORD_RULES.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return category

        # 3. Metadata fallback
        if metadata and metadata.get("stripe_type") == "stripe_fee":
            return "taxes_fees"

        # 4. Default
        return "other"

    async def categorize_batch(
        self,
        user_id: str,
        limit: int = 500,
    ) -> dict[str, int]:
        """Categorize uncategorized Stripe records for a user.

        Queries financial_records WHERE category IS NULL AND source_type = 'stripe',
        categorizes each, and batch-updates the category column.

        Args:
            user_id: The owning user's UUID.
            limit: Maximum records to process in one batch.

        Returns:
            ``{"categorized": N, "skipped": N}`` counts.
        """
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()

        # Query uncategorized Stripe records
        result = await execute_async(
            admin.client.table("financial_records")
            .select("id, description, transaction_type, metadata")
            .eq("user_id", user_id)
            .is_("category", "null")
            .eq("source_type", "stripe")
            .limit(limit),
            op_name="expense_categorization.fetch_uncategorized",
        )

        records = result.data if result.data else []
        if not records:
            return {"categorized": 0, "skipped": 0}

        categorized = 0
        skipped = 0

        for record in records:
            category = self.categorize_transaction(
                description=record.get("description", ""),
                transaction_type=record.get("transaction_type", ""),
                metadata=record.get("metadata"),
            )

            try:
                await execute_async(
                    admin.client.table("financial_records")
                    .update({"category": category})
                    .eq("id", record["id"]),
                    op_name="expense_categorization.update_category",
                )
                categorized += 1
            except Exception:
                logger.warning(
                    "Failed to update category for record=%s", record["id"]
                )
                skipped += 1

        logger.info(
            "Expense categorization batch: user=%s categorized=%d skipped=%d",
            user_id,
            categorized,
            skipped,
        )
        return {"categorized": categorized, "skipped": skipped}

    async def categorize_single(self, record: dict[str, Any]) -> str:
        """Categorize a single record dict (convenience wrapper).

        Args:
            record: Dict with 'description', 'transaction_type', and optional 'metadata'.

        Returns:
            Category name string.
        """
        return self.categorize_transaction(
            description=record.get("description", ""),
            transaction_type=record.get("transaction_type", ""),
            metadata=record.get("metadata"),
        )


def categorize_transaction(
    description: str,
    transaction_type: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Module-level convenience function for one-off categorization.

    Args:
        description: The transaction description text.
        transaction_type: The financial_records transaction_type value.
        metadata: Optional JSONB metadata dict.

    Returns:
        Category name string.
    """
    return ExpenseCategorizationService().categorize_transaction(
        description=description,
        transaction_type=transaction_type,
        metadata=metadata,
    )
