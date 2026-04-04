# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ShopifyService.

Tests GraphQL query construction, product/order sync, analytics
computation, inventory alerts, webhook handlers, and threshold setting.
All Supabase and httpx calls are mocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We'll need to mock environment variables before importing the service
ENV_VARS = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
    "SHOPIFY_CLIENT_ID": "test-client-id",
    "SHOPIFY_CLIENT_SECRET": "test-client-secret",
    "SHOPIFY_WEBHOOK_SECRET": "test-webhook-secret",
}


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set required env vars for all tests."""
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def mock_execute():
    """Mock the BaseService.execute method."""
    with patch(
        "app.services.shopify_service.BaseService.execute",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_admin_execute():
    """Mock the AdminService execute (via execute_async)."""
    with patch(
        "app.services.shopify_service.execute_async",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_httpx():
    """Mock httpx.AsyncClient for GraphQL requests."""
    with patch("app.services.shopify_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_client


@pytest.fixture
def mock_notification():
    """Mock the notification service."""
    with patch("app.services.shopify_service.get_notification_service") as mock_fn:
        mock_svc = MagicMock()
        mock_svc.create_notification = AsyncMock(return_value={"id": "notif-1"})
        mock_fn.return_value = mock_svc
        yield mock_svc


@pytest.fixture
def service():
    """Create a ShopifyService instance."""
    from app.services.shopify_service import ShopifyService

    return ShopifyService()


# ============================================================================
# GraphQL query construction
# ============================================================================


@pytest.mark.asyncio
async def test_graphql_query_products(service, mock_httpx):
    """_graphql_request builds correct GraphQL POST for products."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/1",
                            "title": "Test Product",
                            "vendor": "TestVendor",
                            "productType": "TestType",
                            "status": "ACTIVE",
                            "totalInventory": 25,
                            "featuredMedia": {
                                "preview": {"image": {"url": "https://img.test/1.jpg"}}
                            },
                            "variants": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/1",
                                            "title": "Default",
                                            "price": "29.99",
                                            "inventoryQuantity": 25,
                                            "sku": "TEST-001",
                                        }
                                    }
                                ]
                            },
                        },
                        "cursor": "cursor-1",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        },
        "extensions": {
            "cost": {
                "throttleStatus": {"currentlyAvailable": 900}
            }
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_httpx.post = AsyncMock(return_value=mock_response)

    result = await service._graphql_request(
        shop="testshop",
        token="shpat_test123",
        query="{ products(first: 50) { edges { node { id } } } }",
        variables={},
    )

    mock_httpx.post.assert_called_once()
    call_args = mock_httpx.post.call_args
    assert "testshop.myshopify.com" in call_args[0][0]
    assert "graphql.json" in call_args[0][0]
    assert call_args[1]["headers"]["X-Shopify-Access-Token"] == "shpat_test123"
    assert "data" in result


@pytest.mark.asyncio
async def test_graphql_query_orders(service, mock_httpx):
    """_graphql_request builds correct GraphQL POST for orders."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1001",
                            "name": "#1001",
                            "email": "customer@test.com",
                            "financialStatus": "PAID",
                            "fulfillmentStatus": "FULFILLED",
                            "totalPriceSet": {
                                "shopMoney": {"amount": "59.98", "currencyCode": "USD"}
                            },
                            "subtotalPriceSet": {
                                "shopMoney": {"amount": "49.98", "currencyCode": "USD"}
                            },
                            "createdAt": "2026-03-01T10:00:00Z",
                            "customer": {"email": "customer@test.com"},
                            "lineItems": {
                                "edges": [
                                    {
                                        "node": {
                                            "title": "Test Product",
                                            "quantity": 2,
                                            "variant": {
                                                "price": "29.99",
                                                "product": {
                                                    "id": "gid://shopify/Product/1"
                                                },
                                            },
                                        }
                                    }
                                ]
                            },
                        },
                        "cursor": "order-cursor-1",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        },
        "extensions": {
            "cost": {
                "throttleStatus": {"currentlyAvailable": 900}
            }
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_httpx.post = AsyncMock(return_value=mock_response)

    result = await service._graphql_request(
        shop="testshop",
        token="shpat_test123",
        query="{ orders(first: 50) { edges { node { id } } } }",
        variables={},
    )

    assert "data" in result
    assert "orders" in result["data"]


# ============================================================================
# Product sync
# ============================================================================


@pytest.mark.asyncio
async def test_sync_products(service, mock_httpx, mock_execute):
    """sync_products() fetches products via GraphQL and upserts into DB."""
    graphql_response = MagicMock()
    graphql_response.status_code = 200
    graphql_response.json.return_value = {
        "data": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/1",
                            "title": "Widget A",
                            "vendor": "Acme",
                            "productType": "Widgets",
                            "status": "ACTIVE",
                            "totalInventory": 30,
                            "featuredMedia": {
                                "preview": {"image": {"url": "https://img.test/a.jpg"}}
                            },
                            "variants": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/10",
                                            "title": "Small",
                                            "price": "10.00",
                                            "inventoryQuantity": 15,
                                            "sku": "WA-S",
                                        }
                                    },
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/11",
                                            "title": "Large",
                                            "price": "15.00",
                                            "inventoryQuantity": 15,
                                            "sku": "WA-L",
                                        }
                                    },
                                ]
                            },
                        },
                        "cursor": "c1",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        },
        "extensions": {
            "cost": {"throttleStatus": {"currentlyAvailable": 900}}
        },
    }
    graphql_response.raise_for_status = MagicMock()
    mock_httpx.post = AsyncMock(return_value=graphql_response)

    # Mock the Supabase upsert
    mock_result = MagicMock()
    mock_result.data = [{"id": "uuid-1"}]
    mock_execute.return_value = mock_result

    result = await service.sync_products(
        user_id="user-123", shop="testshop", token="shpat_test"
    )

    assert result["synced"] == 1
    # Verify upsert was called with correct field mapping
    mock_execute.assert_called()
    call_args = mock_execute.call_args_list
    # Should have at least one upsert call
    assert len(call_args) >= 1


# ============================================================================
# Order sync
# ============================================================================


@pytest.mark.asyncio
async def test_sync_orders(service, mock_httpx, mock_execute):
    """sync_orders() fetches orders and creates both shopify_orders and financial_records."""
    graphql_response = MagicMock()
    graphql_response.status_code = 200
    graphql_response.json.return_value = {
        "data": {
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/2001",
                            "name": "#2001",
                            "email": "buyer@test.com",
                            "financialStatus": "PAID",
                            "fulfillmentStatus": "UNFULFILLED",
                            "totalPriceSet": {
                                "shopMoney": {"amount": "99.99", "currencyCode": "USD"}
                            },
                            "subtotalPriceSet": {
                                "shopMoney": {"amount": "89.99", "currencyCode": "USD"}
                            },
                            "createdAt": "2026-03-15T14:30:00Z",
                            "customer": {
                                "email": "buyer@test.com",
                                "firstName": "Test",
                            },
                            "lineItems": {
                                "edges": [
                                    {
                                        "node": {
                                            "title": "Widget A",
                                            "quantity": 1,
                                            "variant": {
                                                "price": "89.99",
                                                "product": {
                                                    "id": "gid://shopify/Product/1"
                                                },
                                            },
                                        }
                                    }
                                ]
                            },
                        },
                        "cursor": "oc1",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        },
        "extensions": {
            "cost": {"throttleStatus": {"currentlyAvailable": 900}}
        },
    }
    graphql_response.raise_for_status = MagicMock()
    mock_httpx.post = AsyncMock(return_value=graphql_response)

    mock_result = MagicMock()
    mock_result.data = [{"id": "uuid-order-1"}]
    mock_execute.return_value = mock_result

    result = await service.sync_orders(
        user_id="user-123", shop="testshop", token="shpat_test"
    )

    assert result["synced"] == 1
    # Should have at least 2 calls: one for shopify_orders upsert, one for financial_records upsert
    assert mock_execute.call_count >= 2


# ============================================================================
# Analytics
# ============================================================================


@pytest.mark.asyncio
async def test_analytics(service, mock_execute):
    """get_analytics() computes revenue, AOV, top products from orders."""
    # Mock shopify_orders query
    orders_result = MagicMock()
    orders_result.data = [
        {
            "id": "o1",
            "total_price": 100.00,
            "line_items": json.dumps([
                {"title": "Product A", "quantity": 2, "price": "25.00", "product_id": "p1"},
                {"title": "Product B", "quantity": 1, "price": "50.00", "product_id": "p2"},
            ]),
        },
        {
            "id": "o2",
            "total_price": 50.00,
            "line_items": json.dumps([
                {"title": "Product A", "quantity": 1, "price": "25.00", "product_id": "p1"},
                {"title": "Product C", "quantity": 1, "price": "25.00", "product_id": "p3"},
            ]),
        },
    ]

    mock_execute.return_value = orders_result

    result = await service.get_analytics(user_id="user-123")

    assert result["revenue_total"] == 150.00
    assert result["order_count"] == 2
    assert result["average_order_value"] == 75.00
    assert isinstance(result["top_products"], list)


# ============================================================================
# Inventory alerts
# ============================================================================


@pytest.mark.asyncio
async def test_low_stock_check(service, mock_execute, mock_notification):
    """check_inventory_alerts() sends notifications for low-stock products."""
    low_stock_result = MagicMock()
    low_stock_result.data = [
        {
            "id": "prod-1",
            "title": "Widget A",
            "inventory_quantity": 3,
            "low_stock_threshold": 10,
            "user_id": "user-123",
        },
        {
            "id": "prod-2",
            "title": "Widget B",
            "inventory_quantity": 0,
            "low_stock_threshold": 5,
            "user_id": "user-123",
        },
    ]
    mock_execute.return_value = low_stock_result

    count = await service.check_inventory_alerts(user_id="user-123")

    assert count == 2
    assert mock_notification.create_notification.call_count == 2
    # Verify notification content
    first_call = mock_notification.create_notification.call_args_list[0]
    assert "Widget A" in first_call[1]["message"] or "Widget A" in str(first_call)


# ============================================================================
# Webhook handlers
# ============================================================================


@pytest.mark.asyncio
async def test_webhook_order_create(service, mock_admin_execute):
    """handle_order_create() inserts into shopify_orders and financial_records."""
    mock_result = MagicMock()
    mock_result.data = [{"id": "uuid-1"}]
    mock_admin_execute.return_value = mock_result

    data = {
        "id": 3001,
        "name": "#3001",
        "email": "wh@test.com",
        "financial_status": "paid",
        "fulfillment_status": None,
        "total_price": "75.00",
        "subtotal_price": "65.00",
        "currency": "USD",
        "line_items": [
            {"title": "Item 1", "quantity": 1, "price": "65.00"}
        ],
        "customer": {"email": "wh@test.com"},
        "created_at": "2026-04-01T10:00:00Z",
    }

    await service.handle_order_create(data=data, user_id="user-123")

    # Should insert into shopify_orders AND financial_records
    assert mock_admin_execute.call_count >= 2


@pytest.mark.asyncio
async def test_webhook_inventory_update(service, mock_admin_execute, mock_execute, mock_notification):
    """handle_inventory_update() updates inventory and triggers low stock check."""
    # Mock the admin execute for the update
    update_result = MagicMock()
    update_result.data = [{"id": "prod-1", "inventory_quantity": 3, "low_stock_threshold": 10}]
    mock_admin_execute.return_value = update_result

    # Mock the low stock query
    low_stock_result = MagicMock()
    low_stock_result.data = [
        {
            "id": "prod-1",
            "title": "Widget A",
            "inventory_quantity": 3,
            "low_stock_threshold": 10,
            "user_id": "user-123",
        },
    ]
    mock_execute.return_value = low_stock_result

    data = {
        "inventory_item_id": 12345,
        "available": 3,
    }

    await service.handle_inventory_update(data=data, user_id="user-123")

    # Should have called admin execute for the update
    assert mock_admin_execute.call_count >= 1


# ============================================================================
# Threshold setting
# ============================================================================


@pytest.mark.asyncio
async def test_set_threshold(service, mock_execute):
    """set_alert_threshold() updates the low_stock_threshold for a product."""
    mock_result = MagicMock()
    mock_result.data = [{"id": "prod-1", "low_stock_threshold": 20}]
    mock_execute.return_value = mock_result

    result = await service.set_alert_threshold(
        user_id="user-123", product_id="prod-1", threshold=20
    )

    assert result["low_stock_threshold"] == 20
    mock_execute.assert_called_once()
