# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""FinancialService - Financial data operations with proper RLS authentication.

This service handles financial data queries with user-scoped authentication.
"""

import logging
from datetime import datetime, timedelta

from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class FinancialService(BaseService):
    """Service for financial data operations.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the financial service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)

    async def get_revenue_stats(self, period: str = "current_month") -> dict:
        """Fetch revenue statistics from the database for the specified period.

        Queries the financial_records table and aggregates revenue data based
        on the period parameter. Falls back to 0 if no data exists.

        Args:
            period: Time period for stats - 'current_month', 'last_month',
                   'current_quarter', 'current_year', or 'all_time'.

        Returns:
            Dictionary with revenue, currency, period, transaction count, and status.
        """
        try:
            # Calculate date range based on period
            now = datetime.now()
            start_date = None
            end_date = None

            if period == "current_month":
                start_date = now.replace(day=1)
                end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(
                    days=1
                )
            elif period == "last_month":
                end_date = now.replace(day=1) - timedelta(days=1)
                start_date = end_date.replace(day=1)
            elif period == "current_quarter":
                quarter = (now.month - 1) // 3
                start_date = now.replace(month=quarter * 3 + 1, day=1)
                end_date = (start_date + timedelta(days=95)).replace(day=1) - timedelta(
                    days=1
                )
            elif period == "current_year":
                start_date = now.replace(month=1, day=1)
                end_date = now.replace(month=12, day=31)
            elif period == "all_time":
                pass  # No date filtering
            # Build query for revenue transactions
            query = self.client.table("financial_records").select(
                "amount, currency, transaction_date, description"
            )
            query = query.eq("transaction_type", "revenue")

            # Apply date range filter if specified
            if start_date and end_date:
                query = query.gte("transaction_date", start_date.isoformat())
                query = query.lte("transaction_date", end_date.isoformat())

            response = await execute_async(query)

            # Calculate totals
            total_revenue = 0.0
            transaction_count = 0
            transactions = []

            if response.data:
                for record in response.data:
                    amount = record.get("amount", 0)
                    if isinstance(amount, (int, float)):
                        total_revenue += amount
                    transaction_count += 1
                    transactions.append(
                        {
                            "amount": amount,
                            "date": record.get("transaction_date"),
                            "description": record.get("description", ""),
                        }
                    )

            # Get currency from first record or default to USD
            currency = "USD"
            if response.data and len(response.data) > 0:
                currency = response.data[0].get("currency", "USD")

            return {
                "revenue": round(total_revenue, 2),
                "currency": currency,
                "period": period,
                "transaction_count": transaction_count,
                "status": "connected",
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                }
                if start_date
                else None,
                "recent_transactions": transactions[:5] if transactions else [],
            }

        except Exception as e:
            logger.error(f"Error fetching revenue stats: {e}")
            return {
                "revenue": 0.0,
                "currency": "USD",
                "period": period,
                "transaction_count": 0,
                "status": "error",
                "error": str(e),
            }
