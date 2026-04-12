# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for VendorOpsService — real implementations replacing degraded ops tools.

OPS-06: update_inventory, create_vendor, create_po must produce real business
records instead of degraded_completed task stubs.
"""

from __future__ import annotations

import os
import re
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure BaseService can initialize without real Supabase credentials
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

# Stub supabase so inventory_service (which does `from supabase import Client`)
# can be imported in a test environment without the real SDK.
if "supabase" not in sys.modules:
    _fake_supabase = types.ModuleType("supabase")
    _fake_client = type("Client", (), {})
    _fake_supabase.Client = _fake_client  # type: ignore[attr-defined]
    _fake_supabase.create_client = MagicMock()  # type: ignore[attr-defined]
    sys.modules["supabase"] = _fake_supabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PO_REF_PATTERN = re.compile(r"^PO-\d{6}-\d{4}$")


# ---------------------------------------------------------------------------
# update_inventory_real tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_inventory_real_with_product_id():
    """Direct path: product_id provided → calls InventoryService.update_stock."""
    mock_inv_service = AsyncMock()
    mock_inv_service.update_stock.return_value = {
        "product_id": "prod-123",
        "new_quantity": 42,
    }

    with patch(
        "app.commerce.inventory_service.InventoryService",
        return_value=mock_inv_service,
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.update_inventory_real(
            user_id="user-1",
            item="Widget",
            quantity=5,
            product_id="prod-123",
        )

    mock_inv_service.update_stock.assert_called_once_with("prod-123", 5)
    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["product_id"] == "prod-123"
    assert result["new_quantity"] == 42
    assert result["tool"] == "update_inventory"
    assert "degraded" not in result["status"]


@pytest.mark.asyncio
async def test_update_inventory_real_with_item_name_found():
    """Name-search path: item name matched in inventory list → calls update_stock."""
    mock_inv_service = AsyncMock()
    mock_inv_service.list_inventory.return_value = [
        {"product_id": "prod-abc", "name": "Blue Widget", "quantity": 10},
        {"product_id": "prod-xyz", "name": "Red Gadget", "quantity": 5},
    ]
    mock_inv_service.update_stock.return_value = {
        "product_id": "prod-abc",
        "new_quantity": 13,
    }

    with patch(
        "app.commerce.inventory_service.InventoryService",
        return_value=mock_inv_service,
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.update_inventory_real(
            user_id="user-1",
            item="blue widget",
            quantity=3,
        )

    mock_inv_service.list_inventory.assert_called_once_with("user-1")
    mock_inv_service.update_stock.assert_called_once_with("prod-abc", 3)
    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["new_quantity"] == 13


@pytest.mark.asyncio
async def test_update_inventory_real_with_item_name_not_found():
    """Name-search path: item name not found → returns error dict."""
    mock_inv_service = AsyncMock()
    mock_inv_service.list_inventory.return_value = [
        {"product_id": "prod-abc", "name": "Blue Widget", "quantity": 10},
    ]

    with patch(
        "app.commerce.inventory_service.InventoryService",
        return_value=mock_inv_service,
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.update_inventory_real(
            user_id="user-1",
            item="Nonexistent Item",
            quantity=5,
        )

    assert result["success"] is False
    assert "not found" in result["error"].lower()
    assert "list_inventory" in result["error"]


@pytest.mark.asyncio
async def test_update_inventory_real_returns_new_quantity():
    """Result always includes new_quantity and product_name."""
    mock_inv_service = AsyncMock()
    mock_inv_service.update_stock.return_value = {
        "product_id": "prod-123",
        "new_quantity": 99,
    }

    with patch(
        "app.commerce.inventory_service.InventoryService",
        return_value=mock_inv_service,
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.update_inventory_real(
            user_id="user-1",
            item="Any Item",
            quantity=10,
            product_id="prod-123",
        )

    assert result["new_quantity"] == 99
    assert result["change"] == 10


# ---------------------------------------------------------------------------
# create_vendor_record tests
# ---------------------------------------------------------------------------


def _mock_client_builder(data: list) -> MagicMock:
    """Build a mock supabase client whose .table().insert().select() chain returns data."""
    mock_result = MagicMock()
    mock_result.data = data

    mock_select = MagicMock()
    mock_select.return_value = mock_select  # chaining

    mock_insert = MagicMock()
    mock_insert.select = mock_select

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_insert

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client, mock_result


@pytest.mark.asyncio
async def test_create_vendor_record_full_inputs():
    """Full inputs: inserts into vendor_subscriptions and returns vendor row."""
    expected_row = {
        "id": "vs-001",
        "user_id": "user-1",
        "name": "Acme Corp",
        "category": "software",
        "monthly_cost": 199.0,
        "billing_cycle": "monthly",
        "is_active": True,
    }
    mock_client, mock_result = _mock_client_builder([expected_row])
    mock_execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.services.vendor_ops_service.execute_async", mock_execute),
        patch(
            "app.services.vendor_ops_service._get_service_client",
            return_value=mock_client,
        ),
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.create_vendor_record(
            user_id="user-1",
            name="Acme Corp",
            category="software",
            monthly_cost=199.0,
        )

    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["vendor"]["name"] == "Acme Corp"
    assert result["tool"] == "create_vendor"
    assert "degraded" not in result["status"]


@pytest.mark.asyncio
async def test_create_vendor_record_minimal_inputs():
    """Minimal inputs: only name provided; defaults applied."""
    expected_row = {
        "id": "vs-002",
        "user_id": "user-1",
        "name": "Basic Vendor",
        "category": "other",
        "monthly_cost": 0,
        "billing_cycle": "monthly",
        "is_active": True,
    }
    mock_client, mock_result = _mock_client_builder([expected_row])
    mock_execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.services.vendor_ops_service.execute_async", mock_execute),
        patch(
            "app.services.vendor_ops_service._get_service_client",
            return_value=mock_client,
        ),
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.create_vendor_record(
            user_id="user-1",
            name="Basic Vendor",
        )

    assert result["success"] is True
    assert result["vendor"]["category"] == "other"


@pytest.mark.asyncio
async def test_create_vendor_record_returns_completed_not_degraded():
    """Status must be 'completed', not 'degraded_completed'."""
    mock_client, mock_result = _mock_client_builder([{"id": "vs-003", "name": "Vendor X"}])
    mock_execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.services.vendor_ops_service.execute_async", mock_execute),
        patch(
            "app.services.vendor_ops_service._get_service_client",
            return_value=mock_client,
        ),
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.create_vendor_record(user_id="user-1", name="Vendor X")

    assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# create_purchase_order tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_purchase_order_returns_po_reference():
    """PO reference is generated in format PO-YYMMDD-NNNN."""
    mock_task = {"id": "task-001", "status": "pending", "description": "PO task"}

    with patch(
        "app.services.vendor_ops_service.create_task",
        new=AsyncMock(return_value={"task_id": "task-001", "task": mock_task, "success": True}),
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.create_purchase_order(
            user_id="user-1",
            vendor="Acme Corp",
            amount=1500.0,
        )

    assert result["success"] is True
    assert result["status"] == "completed"
    assert PO_REF_PATTERN.match(result["po_reference"]), (
        f"PO reference '{result['po_reference']}' does not match PO-YYMMDD-NNNN"
    )
    assert result["vendor"] == "Acme Corp"
    assert result["total_amount"] == 1500.0
    assert result["tool"] == "create_po"


@pytest.mark.asyncio
async def test_create_purchase_order_with_items():
    """Items list is included in result when provided."""
    items = [{"sku": "WIDGET-01", "qty": 10, "unit_price": 15.0}]

    with patch(
        "app.services.vendor_ops_service.create_task",
        new=AsyncMock(return_value={"task_id": "t1", "task": {}, "success": True}),
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.create_purchase_order(
            user_id="user-1",
            vendor="Widget Co",
            amount=150.0,
            items=items,
        )

    assert result["items"] == items


@pytest.mark.asyncio
async def test_create_purchase_order_status_completed():
    """Status must be 'completed', not 'degraded_completed'."""
    with patch(
        "app.services.vendor_ops_service.create_task",
        new=AsyncMock(return_value={"task_id": "t1", "task": {}, "success": True}),
    ):
        from app.services.vendor_ops_service import VendorOpsService

        svc = VendorOpsService()
        result = await svc.create_purchase_order(user_id="user-1", vendor="X")

    assert result["status"] == "completed"
    assert "degraded" not in result["status"]


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_inventory_module_level_accepts_kwargs():
    """Module-level update_inventory wrapper accepts **kwargs without error."""
    mock_inv_service = AsyncMock()
    mock_inv_service.update_stock.return_value = {"product_id": "p1", "new_quantity": 5}

    with patch(
        "app.commerce.inventory_service.InventoryService",
        return_value=mock_inv_service,
    ):
        with patch(
            "app.services.vendor_ops_service.get_current_user_id",
            return_value="user-1",
        ):
            from app.services import vendor_ops_service

            result = await vendor_ops_service.update_inventory(
                item="Widget",
                quantity=5,
                product_id="p1",
                extra_kwarg="ignored",
            )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_create_vendor_module_level_accepts_kwargs():
    """Module-level create_vendor wrapper accepts **kwargs without error."""
    mock_client, mock_result = _mock_client_builder([{"id": "v1", "name": "Acme"}])
    mock_execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.services.vendor_ops_service.execute_async", mock_execute),
        patch(
            "app.services.vendor_ops_service._get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.services.vendor_ops_service.get_current_user_id",
            return_value="user-1",
        ),
    ):
        from app.services import vendor_ops_service

        result = await vendor_ops_service.create_vendor(
            name="Acme",
            extra_kwarg="ignored",
        )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_create_po_module_level_accepts_kwargs():
    """Module-level create_po wrapper accepts **kwargs without error."""
    with patch(
        "app.services.vendor_ops_service.create_task",
        new=AsyncMock(return_value={"task_id": "t1", "task": {}, "success": True}),
    ):
        with patch(
            "app.services.vendor_ops_service.get_current_user_id",
            return_value="user-1",
        ):
            from app.services import vendor_ops_service

            result = await vendor_ops_service.create_po(
                vendor="Acme",
                amount=500.0,
                extra_kwarg="ignored",
            )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_all_functions_return_completed_not_degraded():
    """All three functions must return status='completed'."""
    mock_inv = AsyncMock()
    mock_inv.update_stock.return_value = {"product_id": "p1", "new_quantity": 1}
    mock_client, mock_result = _mock_client_builder([{"id": "v1", "name": "V"}])
    mock_exec = AsyncMock(return_value=mock_result)

    with (
        patch("app.commerce.inventory_service.InventoryService", return_value=mock_inv),
        patch("app.services.vendor_ops_service.execute_async", mock_exec),
        patch(
            "app.services.vendor_ops_service._get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.services.vendor_ops_service.create_task",
            new=AsyncMock(return_value={"task_id": "t1", "task": {}, "success": True}),
        ),
        patch(
            "app.services.vendor_ops_service.get_current_user_id",
            return_value="user-1",
        ),
    ):
        from app.services import vendor_ops_service

        r1 = await vendor_ops_service.update_inventory(
            item="X", quantity=1, product_id="p1"
        )
        r2 = await vendor_ops_service.create_vendor(name="V")
        r3 = await vendor_ops_service.create_po(vendor="V", amount=10.0)

    for r in (r1, r2, r3):
        assert r["status"] == "completed", f"Expected 'completed', got '{r['status']}'"
        assert "degraded" not in r["status"]
