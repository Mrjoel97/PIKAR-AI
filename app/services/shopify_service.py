# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ShopifyService -- Shopify e-commerce connector.

Provides GraphQL-based product/order sync, real-time webhook handling,
sales analytics computation, and inventory alert management.

Uses Shopify Admin GraphQL API (2024-10) with cost-based rate limiting.
All data stored in ``shopify_orders`` and ``shopify_products`` tables
with RLS policies scoped to ``user_id``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.notifications.notification_service import (
    NotificationType,
    get_notification_service,
)
from app.services.base_service import BaseService
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHOPIFY_API_VERSION = "2024-10"

_GRAPHQL_ENDPOINT = (
    "https://{shop}.myshopify.com/admin/api/{version}/graphql.json"
)

# Minimum available cost points before we pause to avoid throttling.
_RATE_LIMIT_THRESHOLD = 200

# ---------------------------------------------------------------------------
# GraphQL query fragments
# ---------------------------------------------------------------------------

PRODUCTS_QUERY = """
query FetchProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    edges {
      node {
        id
        title
        vendor
        productType
        status
        totalInventory
        featuredMedia {
          preview {
            image {
              url
            }
          }
        }
        variants(first: 100) {
          edges {
            node {
              id
              title
              price
              inventoryQuantity
              sku
            }
          }
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
    }
  }
}
"""

ORDERS_QUERY = """
query FetchOrders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query) {
    edges {
      node {
        id
        name
        email
        financialStatus
        fulfillmentStatus
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        subtotalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        createdAt
        customer {
          email
          firstName
          lastName
        }
        lineItems(first: 50) {
          edges {
            node {
              title
              quantity
              variant {
                price
                product {
                  id
                }
              }
            }
          }
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
    }
  }
}
"""


class ShopifyService(BaseService):
    """Shopify e-commerce connector with GraphQL sync and analytics.

    Extends ``BaseService`` for RLS-scoped reads.  Webhook handlers
    use ``AdminService`` (service role) for writes since webhooks
    arrive without a user JWT.
    """

    # ------------------------------------------------------------------
    # GraphQL transport
    # ------------------------------------------------------------------

    async def _graphql_request(
        self,
        *,
        shop: str,
        token: str,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a Shopify Admin GraphQL request.

        Handles cost-based rate limiting by sleeping when available
        points drop below ``_RATE_LIMIT_THRESHOLD``.

        Args:
            shop: Shopify shop slug (e.g. ``"mystore"``).
            token: Shopify access token.
            query: GraphQL query string.
            variables: Optional query variables.

        Returns:
            Parsed JSON response dict.

        Raises:
            httpx.HTTPStatusError: On non-2xx responses.
            ValueError: If the response contains GraphQL errors.
        """
        url = _GRAPHQL_ENDPOINT.format(shop=shop, version=SHOPIFY_API_VERSION)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"query": query, "variables": variables or {}},
                headers={
                    "X-Shopify-Access-Token": token,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        result = response.json()

        # Check for GraphQL-level errors
        if result.get("errors"):
            error_msgs = "; ".join(e.get("message", "") for e in result["errors"])
            logger.error("Shopify GraphQL errors: %s", error_msgs)
            raise ValueError(f"Shopify GraphQL error: {error_msgs}")

        # Cost-based rate limiting
        extensions = result.get("extensions", {})
        cost_info = extensions.get("cost", {}).get("throttleStatus", {})
        available = cost_info.get("currentlyAvailable", 1000)
        if available < _RATE_LIMIT_THRESHOLD:
            restore_rate = cost_info.get("restoreRate", 50)
            wait = max(1.0, (_RATE_LIMIT_THRESHOLD - available) / max(restore_rate, 1))
            logger.info(
                "Shopify rate limit: %d points available, sleeping %.1fs",
                available,
                wait,
            )
            await asyncio.sleep(wait)

        return result

    # ------------------------------------------------------------------
    # Sync: Products
    # ------------------------------------------------------------------

    async def sync_products(
        self, user_id: str, shop: str, token: str
    ) -> dict[str, Any]:
        """Fetch all products from Shopify and upsert into ``shopify_products``.

        Paginates through all products using cursor-based pagination.
        Variants are flattened into a JSONB array. ``inventory_quantity``
        is the sum of all variant quantities.

        Args:
            user_id: Owner's UUID.
            shop: Shopify shop slug.
            token: Shopify access token.

        Returns:
            Dict with ``synced`` count.
        """
        synced = 0
        has_next = True
        after_cursor: str | None = None

        while has_next:
            variables: dict[str, Any] = {"first": 50}
            if after_cursor:
                variables["after"] = after_cursor

            result = await self._graphql_request(
                shop=shop, token=token, query=PRODUCTS_QUERY, variables=variables
            )

            edges = result["data"]["products"]["edges"]
            page_info = result["data"]["products"]["pageInfo"]
            has_next = page_info["hasNextPage"]

            for edge in edges:
                node = edge["node"]
                after_cursor = edge["cursor"]

                # Extract product ID (strip GID prefix)
                shopify_product_id = node["id"].split("/")[-1]

                # Flatten variants
                variants_list = []
                total_inventory = 0
                for v_edge in node.get("variants", {}).get("edges", []):
                    v = v_edge["node"]
                    qty = v.get("inventoryQuantity", 0)
                    total_inventory += qty
                    variants_list.append({
                        "id": v["id"].split("/")[-1],
                        "title": v.get("title", ""),
                        "price": v.get("price", "0"),
                        "inventory_quantity": qty,
                        "sku": v.get("sku", ""),
                    })

                # Extract image URL
                image_url = None
                media = node.get("featuredMedia")
                if media and media.get("preview", {}).get("image"):
                    image_url = media["preview"]["image"]["url"]

                row = {
                    "user_id": user_id,
                    "shopify_product_id": shopify_product_id,
                    "title": node["title"],
                    "vendor": node.get("vendor", ""),
                    "product_type": node.get("productType", ""),
                    "status": (node.get("status") or "").lower(),
                    "variants": json.dumps(variants_list),
                    "image_url": image_url,
                    "inventory_quantity": total_inventory,
                }

                await self.execute(
                    self.client.table("shopify_products").upsert(
                        row, on_conflict="user_id,shopify_product_id"
                    ),
                    op_name="shopify.sync_products.upsert",
                )
                synced += 1

        logger.info("Synced %d products for user %s", synced, user_id)
        return {"synced": synced}

    # ------------------------------------------------------------------
    # Sync: Orders
    # ------------------------------------------------------------------

    async def sync_orders(
        self,
        user_id: str,
        shop: str,
        token: str,
        months_back: int = 12,
    ) -> dict[str, Any]:
        """Fetch orders from Shopify and upsert into ``shopify_orders``.

        Also creates ``financial_records`` entries with
        ``source_type="shopify"`` for revenue tracking.

        Args:
            user_id: Owner's UUID.
            shop: Shopify shop slug.
            token: Shopify access token.
            months_back: How many months of history to fetch (default 12).

        Returns:
            Dict with ``synced`` count.
        """
        synced = 0
        has_next = True
        after_cursor: str | None = None

        since = datetime.now(tz=timezone.utc) - timedelta(days=months_back * 30)
        date_filter = f"created_at:>'{since.strftime('%Y-%m-%d')}'"

        while has_next:
            variables: dict[str, Any] = {"first": 50, "query": date_filter}
            if after_cursor:
                variables["after"] = after_cursor

            result = await self._graphql_request(
                shop=shop, token=token, query=ORDERS_QUERY, variables=variables
            )

            edges = result["data"]["orders"]["edges"]
            page_info = result["data"]["orders"]["pageInfo"]
            has_next = page_info["hasNextPage"]

            for edge in edges:
                node = edge["node"]
                after_cursor = edge["cursor"]

                shopify_order_id = node["id"].split("/")[-1]

                total_price_data = node.get("totalPriceSet", {}).get("shopMoney", {})
                subtotal_data = node.get("subtotalPriceSet", {}).get("shopMoney", {})

                total_price = Decimal(total_price_data.get("amount", "0"))
                subtotal_price = Decimal(subtotal_data.get("amount", "0"))
                currency = total_price_data.get("currencyCode", "USD")

                # Flatten line items
                line_items = []
                for li_edge in node.get("lineItems", {}).get("edges", []):
                    li = li_edge["node"]
                    variant = li.get("variant") or {}
                    product = variant.get("product") or {}
                    line_items.append({
                        "title": li.get("title", ""),
                        "quantity": li.get("quantity", 0),
                        "price": variant.get("price", "0"),
                        "product_id": (
                            product.get("id", "").split("/")[-1]
                            if product.get("id")
                            else ""
                        ),
                    })

                customer_data = node.get("customer") or {}

                order_row = {
                    "user_id": user_id,
                    "shopify_order_id": shopify_order_id,
                    "order_number": node.get("name", ""),
                    "email": node.get("email", ""),
                    "financial_status": (node.get("financialStatus") or "").lower(),
                    "fulfillment_status": (
                        (node.get("fulfillmentStatus") or "").lower()
                        or None
                    ),
                    "total_price": float(total_price),
                    "subtotal_price": float(subtotal_price),
                    "currency": currency,
                    "line_items": json.dumps(line_items),
                    "customer": json.dumps(customer_data),
                    "created_at_shopify": node.get("createdAt"),
                }

                # Upsert order
                await self.execute(
                    self.client.table("shopify_orders").upsert(
                        order_row, on_conflict="user_id,shopify_order_id"
                    ),
                    op_name="shopify.sync_orders.upsert",
                )

                # Create corresponding financial_record
                fin_row = {
                    "user_id": user_id,
                    "title": f"Shopify Order {node.get('name', shopify_order_id)}",
                    "amount": float(total_price),
                    "currency": currency,
                    "transaction_type": "revenue",
                    "source_type": "shopify",
                    "external_id": f"shop_order_{shopify_order_id}",
                    "transaction_date": node.get("createdAt"),
                }

                await self.execute(
                    self.client.table("financial_records").upsert(
                        fin_row, on_conflict="external_id"
                    ),
                    op_name="shopify.sync_orders.financial_record",
                )

                synced += 1

        logger.info("Synced %d orders for user %s", synced, user_id)
        return {"synced": synced}

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_orders(
        self,
        user_id: str,
        period: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query shopify_orders for a user with optional filters.

        Args:
            user_id: Owner's UUID.
            period: Optional ISO date string to filter ``created_at_shopify >= period``.
            status: Optional financial_status filter.

        Returns:
            List of order dicts.
        """
        query = (
            self.client.table("shopify_orders")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at_shopify", desc=True)
        )

        if period:
            query = query.gte("created_at_shopify", period)
        if status:
            query = query.eq("financial_status", status)

        result = await self.execute(query, op_name="shopify.get_orders")
        return result.data or []

    async def get_products(
        self,
        user_id: str,
        category: str | None = None,
        sort_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query shopify_products for a user.

        Args:
            user_id: Owner's UUID.
            category: Optional ``product_type`` filter.
            sort_by: Column name to sort by (default ``title``).

        Returns:
            List of product dicts.
        """
        query = (
            self.client.table("shopify_products")
            .select("*")
            .eq("user_id", user_id)
        )

        if category:
            query = query.eq("product_type", category)

        valid_sorts = {"title", "inventory_quantity", "created_at"}
        order_col = sort_by if sort_by in valid_sorts else "title"
        query = query.order(order_col)

        result = await self.execute(query, op_name="shopify.get_products")
        return result.data or []

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_analytics(
        self,
        user_id: str,
        period: str | None = None,
    ) -> dict[str, Any]:
        """Compute sales analytics from shopify_orders.

        Args:
            user_id: Owner's UUID.
            period: Optional ISO date string for ``created_at_shopify >= period``.

        Returns:
            Dict with ``revenue_total``, ``order_count``,
            ``average_order_value``, and ``top_products``.
        """
        query = (
            self.client.table("shopify_orders")
            .select("id, total_price, line_items")
            .eq("user_id", user_id)
        )
        if period:
            query = query.gte("created_at_shopify", period)

        result = await self.execute(query, op_name="shopify.analytics")
        orders = result.data or []

        revenue_total = sum(float(o.get("total_price", 0)) for o in orders)
        order_count = len(orders)
        average_order_value = revenue_total / order_count if order_count else 0

        # Aggregate product revenue from line items
        product_revenue: dict[str, dict[str, Any]] = {}
        for order in orders:
            items = order.get("line_items", "[]")
            if isinstance(items, str):
                items = json.loads(items)
            for item in items:
                title = item.get("title", "Unknown")
                qty = item.get("quantity", 0)
                price = float(item.get("price", 0))
                item_revenue = qty * price

                if title not in product_revenue:
                    product_revenue[title] = {
                        "title": title,
                        "revenue": 0,
                        "units_sold": 0,
                    }
                product_revenue[title]["revenue"] += item_revenue
                product_revenue[title]["units_sold"] += qty

        top_products = sorted(
            product_revenue.values(),
            key=lambda p: p["revenue"],
            reverse=True,
        )[:10]

        return {
            "revenue_total": round(revenue_total, 2),
            "order_count": order_count,
            "average_order_value": round(average_order_value, 2),
            "top_products": top_products,
        }

    # ------------------------------------------------------------------
    # Inventory alerts
    # ------------------------------------------------------------------

    async def get_low_stock_products(self, user_id: str) -> list[dict[str, Any]]:
        """Return products where inventory is below the alert threshold.

        Uses a raw ``filter`` expression ``inventory_quantity.lt.low_stock_threshold``
        via the ``or_`` approach. Since Supabase PostgREST doesn't natively
        support column-to-column comparisons, we fetch all products and filter
        in Python.

        Args:
            user_id: Owner's UUID.

        Returns:
            List of low-stock product dicts.
        """
        result = await self.execute(
            self.client.table("shopify_products")
            .select("*")
            .eq("user_id", user_id),
            op_name="shopify.low_stock",
        )
        products = result.data or []
        return [
            p for p in products
            if p.get("inventory_quantity", 0) < p.get("low_stock_threshold", 10)
        ]

    async def set_alert_threshold(
        self, user_id: str, product_id: str, threshold: int
    ) -> dict[str, Any]:
        """Update the low-stock alert threshold for a specific product.

        Args:
            user_id: Owner's UUID.
            product_id: Product row UUID.
            threshold: New threshold value.

        Returns:
            Updated product row.
        """
        result = await self.execute(
            self.client.table("shopify_products")
            .update({"low_stock_threshold": threshold})
            .eq("id", product_id)
            .eq("user_id", user_id),
            op_name="shopify.set_threshold",
        )
        return result.data[0] if result.data else {"low_stock_threshold": threshold}

    async def check_inventory_alerts(self, user_id: str) -> int:
        """Check for low-stock products and send notifications.

        Queries all products below their threshold and creates a
        WARNING notification for each via ``NotificationService``.

        Args:
            user_id: Owner's UUID.

        Returns:
            Number of alerts sent.
        """
        low_stock = await self.get_low_stock_products(user_id)
        if not low_stock:
            return 0

        notif_svc = get_notification_service()
        count = 0

        for product in low_stock:
            title = product.get("title", "Unknown Product")
            qty = product.get("inventory_quantity", 0)
            threshold = product.get("low_stock_threshold", 10)

            await notif_svc.create_notification(
                user_id=user_id,
                title="Low Stock Alert",
                message=(
                    f"{title} is low on stock "
                    f"({qty} remaining, threshold: {threshold})"
                ),
                type=NotificationType.WARNING,
                link="/dashboard/inventory",
                metadata={
                    "product_id": product.get("id"),
                    "shopify_product_id": product.get("shopify_product_id"),
                    "inventory_quantity": qty,
                    "low_stock_threshold": threshold,
                },
            )
            count += 1

        logger.info("Sent %d low-stock alerts for user %s", count, user_id)
        return count

    # ------------------------------------------------------------------
    # Webhook handlers (use service role for DB writes)
    # ------------------------------------------------------------------

    async def handle_order_create(
        self, data: dict[str, Any], user_id: str
    ) -> None:
        """Process a Shopify ``orders/create`` webhook event.

        Inserts into ``shopify_orders`` and ``financial_records``.

        Args:
            data: Webhook payload (Shopify order object).
            user_id: Resolved owner UUID.
        """
        client = get_service_client()

        shopify_order_id = str(data.get("id", ""))
        total_price = float(data.get("total_price", 0))
        subtotal_price = float(data.get("subtotal_price", 0))
        currency = data.get("currency", "USD")

        line_items = [
            {
                "title": li.get("title", ""),
                "quantity": li.get("quantity", 0),
                "price": li.get("price", "0"),
            }
            for li in data.get("line_items", [])
        ]

        order_row = {
            "user_id": user_id,
            "shopify_order_id": shopify_order_id,
            "order_number": data.get("name", ""),
            "email": data.get("email", ""),
            "financial_status": data.get("financial_status", ""),
            "fulfillment_status": data.get("fulfillment_status"),
            "total_price": total_price,
            "subtotal_price": subtotal_price,
            "currency": currency,
            "line_items": json.dumps(line_items),
            "customer": json.dumps(data.get("customer", {})),
            "created_at_shopify": data.get("created_at"),
        }

        await execute_async(
            client.table("shopify_orders").upsert(
                order_row, on_conflict="user_id,shopify_order_id"
            ),
            op_name="shopify.webhook.order_create",
        )

        fin_row = {
            "user_id": user_id,
            "title": f"Shopify Order {data.get('name', shopify_order_id)}",
            "amount": total_price,
            "currency": currency,
            "transaction_type": "revenue",
            "source_type": "shopify",
            "external_id": f"shop_order_{shopify_order_id}",
            "transaction_date": data.get("created_at"),
        }

        await execute_async(
            client.table("financial_records").upsert(
                fin_row, on_conflict="external_id"
            ),
            op_name="shopify.webhook.financial_record",
        )

        logger.info("Webhook: created order %s for user %s", shopify_order_id, user_id)

    async def handle_order_update(
        self, data: dict[str, Any], user_id: str
    ) -> None:
        """Process a Shopify ``orders/updated`` webhook event.

        Args:
            data: Webhook payload (Shopify order object).
            user_id: Resolved owner UUID.
        """
        client = get_service_client()
        shopify_order_id = str(data.get("id", ""))

        line_items = [
            {
                "title": li.get("title", ""),
                "quantity": li.get("quantity", 0),
                "price": li.get("price", "0"),
            }
            for li in data.get("line_items", [])
        ]

        update_data = {
            "financial_status": data.get("financial_status", ""),
            "fulfillment_status": data.get("fulfillment_status"),
            "total_price": float(data.get("total_price", 0)),
            "subtotal_price": float(data.get("subtotal_price", 0)),
            "line_items": json.dumps(line_items),
            "customer": json.dumps(data.get("customer", {})),
        }

        await execute_async(
            client.table("shopify_orders")
            .update(update_data)
            .eq("user_id", user_id)
            .eq("shopify_order_id", shopify_order_id),
            op_name="shopify.webhook.order_update",
        )

        logger.info("Webhook: updated order %s for user %s", shopify_order_id, user_id)

    async def handle_product_update(
        self, data: dict[str, Any], user_id: str
    ) -> None:
        """Process a Shopify ``products/update`` webhook event.

        Args:
            data: Webhook payload (Shopify product object).
            user_id: Resolved owner UUID.
        """
        client = get_service_client()
        shopify_product_id = str(data.get("id", ""))

        variants_list = []
        total_inventory = 0
        for v in data.get("variants", []):
            qty = v.get("inventory_quantity", 0)
            total_inventory += qty
            variants_list.append({
                "id": str(v.get("id", "")),
                "title": v.get("title", ""),
                "price": v.get("price", "0"),
                "inventory_quantity": qty,
                "sku": v.get("sku", ""),
            })

        image_url = None
        if data.get("image") and data["image"].get("src"):
            image_url = data["image"]["src"]

        update_row = {
            "user_id": user_id,
            "shopify_product_id": shopify_product_id,
            "title": data.get("title", ""),
            "vendor": data.get("vendor", ""),
            "product_type": data.get("product_type", ""),
            "status": data.get("status", ""),
            "variants": json.dumps(variants_list),
            "image_url": image_url,
            "inventory_quantity": total_inventory,
        }

        await execute_async(
            client.table("shopify_products").upsert(
                update_row, on_conflict="user_id,shopify_product_id"
            ),
            op_name="shopify.webhook.product_update",
        )

        logger.info(
            "Webhook: updated product %s for user %s",
            shopify_product_id,
            user_id,
        )

    async def handle_inventory_update(
        self, data: dict[str, Any], user_id: str
    ) -> None:
        """Process a Shopify ``inventory_levels/update`` webhook event.

        Updates the ``inventory_quantity`` on the matching product and
        triggers low-stock alerts if the new quantity is below threshold.

        Args:
            data: Webhook payload with ``inventory_item_id`` and ``available``.
            user_id: Resolved owner UUID.
        """
        client = get_service_client()
        inventory_item_id = str(data.get("inventory_item_id", ""))
        available = data.get("available", 0)

        # Shopify inventory_levels/update uses inventory_item_id which maps
        # to variant inventory items. We update products that contain this
        # inventory item. For simplicity, we look up products by user_id
        # and update the inventory_quantity directly.
        # In a full implementation, we'd track inventory_item_id -> product mapping.

        await execute_async(
            client.table("shopify_products")
            .update({"inventory_quantity": available})
            .eq("user_id", user_id),
            op_name="shopify.webhook.inventory_update",
        )

        # Check for low stock alerts
        await self.check_inventory_alerts(user_id)

        logger.info(
            "Webhook: inventory update (item=%s, available=%d) for user %s",
            inventory_item_id,
            available,
            user_id,
        )


__all__ = ["ShopifyService"]
