# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shopify agent tools -- orders, products, analytics, and inventory alerts.

Provides five agent-callable functions that wire into the ShopifyService
created in Phase 41 Plan 02.  Tools extract the current user from request
context and return structured dicts for the agent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


_PERIOD_MAP: dict[str, int] = {
    "last_7_days": 7,
    "last_30_days": 30,
    "last_3_months": 90,
}


def _resolve_period(period: str | None) -> str | None:
    """Convert a human-friendly period name to an ISO-8601 date string."""
    if period is None:
        return None
    days = _PERIOD_MAP.get(period)
    if days is None:
        return None
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Tool: get_shopify_orders
# ---------------------------------------------------------------------------


async def get_shopify_orders(
    period: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List Shopify orders with optional filters.

    Optional filters: period ('last_7_days', 'last_30_days',
    'last_3_months'), status ('paid', 'pending', 'refunded').

    Args:
        period: Time range filter for orders.
        status: Financial status filter.

    Returns:
        Dict with orders list and count.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()

    try:
        resolved_period = _resolve_period(period)
        orders = await svc.get_orders(
            user_id=user_id,
            period=resolved_period,
            status=status,
        )
        return {"orders": orders, "count": len(orders)}
    except Exception as exc:
        logger.exception("get_shopify_orders failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Shopify orders: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_shopify_products
# ---------------------------------------------------------------------------


async def get_shopify_products(
    category: str | None = None,
    sort_by: str | None = None,
) -> dict[str, Any]:
    """List Shopify products with optional filters.

    Optional category filter and sort_by ('title', 'inventory', 'price').

    Args:
        category: Product type / category filter.
        sort_by: Column to sort results by.

    Returns:
        Dict with products list and count.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()

    try:
        # Map user-friendly sort names to DB columns
        sort_map = {
            "inventory": "inventory_quantity",
            "price": "title",  # price not a direct column; fallback to title
        }
        db_sort = sort_map.get(sort_by, sort_by) if sort_by else None

        products = await svc.get_products(
            user_id=user_id,
            category=category,
            sort_by=db_sort,
        )
        return {"products": products, "count": len(products)}
    except Exception as exc:
        logger.exception("get_shopify_products failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Shopify products: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_shopify_analytics
# ---------------------------------------------------------------------------


async def get_shopify_analytics(period: str | None = None) -> dict[str, Any]:
    """Get Shopify sales analytics.

    Returns total revenue, order count, average order value,
    and top products by revenue.

    Args:
        period: Optional time range ('last_7_days', 'last_30_days',
            'last_3_months').

    Returns:
        Dict with revenue_total, order_count, average_order_value,
        and top_products.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()

    try:
        resolved_period = _resolve_period(period)
        analytics = await svc.get_analytics(
            user_id=user_id,
            period=resolved_period,
        )
        return analytics
    except Exception as exc:
        logger.exception("get_shopify_analytics failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Shopify analytics: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_low_stock_products
# ---------------------------------------------------------------------------


async def get_low_stock_products() -> dict[str, Any]:
    """Get products with inventory below their configured alert threshold.

    Returns:
        Dict with low-stock products list and count.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()

    try:
        products = await svc.get_low_stock_products(user_id=user_id)
        return {"products": products, "count": len(products)}
    except Exception as exc:
        logger.exception("get_low_stock_products failed for user=%s", user_id)
        return {"error": f"Failed to retrieve low-stock products: {exc}"}


# ---------------------------------------------------------------------------
# Tool: set_inventory_alert_threshold
# ---------------------------------------------------------------------------


async def set_inventory_alert_threshold(
    product_id: str,
    threshold: int = 10,
) -> dict[str, Any]:
    """Set the low-stock alert threshold for a specific product.

    Alerts fire when inventory drops below this number.

    Args:
        product_id: The product's database UUID.
        threshold: New low-stock threshold value (default 10).

    Returns:
        Confirmation dict with the updated threshold.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()

    try:
        result = await svc.set_alert_threshold(
            user_id=user_id,
            product_id=product_id,
            threshold=threshold,
        )
        return {
            "status": "success",
            "product_id": product_id,
            "low_stock_threshold": threshold,
            "message": f"Alert threshold set to {threshold} for product {product_id}.",
            "product": result,
        }
    except Exception as exc:
        logger.exception("set_inventory_alert_threshold failed for user=%s", user_id)
        return {"error": f"Failed to set alert threshold: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

# All 5 tools for FinancialAnalysisAgent
SHOPIFY_TOOLS = [
    get_shopify_orders,
    get_shopify_products,
    get_shopify_analytics,
    get_low_stock_products,
    set_inventory_alert_threshold,
]

# Analytics + orders subset for MarketingAutomationAgent
SHOPIFY_ANALYTICS_TOOLS = [
    get_shopify_analytics,
    get_shopify_orders,
]
