# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""VendorOpsService — Real implementations for vendor and purchase order tools.

Replaces three degraded operations tool placeholders (OPS-06):

- ``update_inventory`` — delegates to InventoryService.update_stock for real
  product stock updates.
- ``create_vendor`` — creates a real vendor_subscriptions record in Supabase.
- ``create_po`` — generates a PO reference number and creates a tracked task.

Module-level wrapper functions match the degraded tool call signatures exactly
so the tool registry can swap them in without changing workflow definitions.

Usage::

    from app.services.vendor_ops_service import VendorOpsService

    svc = VendorOpsService()
    result = await svc.update_inventory_real(user_id, item="Widget", quantity=5)
    vendor = await svc.create_vendor_record(user_id, name="Acme Corp")
    po = await svc.create_purchase_order(user_id, vendor="Acme Corp", amount=1500.0)
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any

from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


async def create_task(description: str) -> dict[str, Any]:
    """Create a task via the shared sales tool create_task.

    Module-level wrapper so tests can patch
    ``app.services.vendor_ops_service.create_task`` without triggering
    the full agent import chain at module load.

    Args:
        description: Task description.

    Returns:
        Task result dict from the underlying create_task tool.
    """
    from app.agents.sales.tools import create_task as _create_task

    return await _create_task(description)


def _get_service_client():
    """Return the Supabase service-role client.

    Module-level wrapper so tests can patch
    ``app.services.vendor_ops_service._get_service_client`` without
    triggering the full supabase import chain at module load.
    """
    from app.services.supabase import get_service_client

    return get_service_client()


class VendorOpsService:
    """Real implementations for vendor, inventory, and purchase-order operations.

    Methods here are intentionally stateless (no __init__ state needed beyond
    lazy imports) so instances are cheap to create per request.
    """

    # ------------------------------------------------------------------
    # update_inventory_real
    # ------------------------------------------------------------------

    async def update_inventory_real(
        self,
        user_id: str,
        item: str = "Inventory item",
        quantity: int | None = None,
        product_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update product stock via InventoryService.update_stock.

        If ``product_id`` is provided, calls update_stock directly.
        Otherwise, searches the inventory list for a product whose name
        contains ``item`` (case-insensitive) and then calls update_stock
        with the matched product's ID.

        Args:
            user_id: Authenticated user identifier.
            item: Human-readable product name (used when product_id not given).
            quantity: Stock change amount (delta). Defaults to 0 if not given.
            product_id: Direct product UUID for fast path. Optional.
            **kwargs: Ignored — accepted for backward-compat with degraded signature.

        Returns:
            dict with success, status, product_id, product_name, new_quantity,
            change, and tool keys on success; success=False + error on failure.
        """
        from app.commerce.inventory_service import InventoryService

        inv_service = InventoryService()
        change = quantity if quantity is not None else 0

        if product_id:
            # Fast path: caller already knows the product ID
            update_result = await inv_service.update_stock(product_id, change)
            if "error" in update_result:
                return {
                    "success": False,
                    "error": update_result["error"],
                    "tool": "update_inventory",
                }
            return {
                "success": True,
                "status": "completed",
                "product_id": product_id,
                "product_name": item,
                "new_quantity": update_result.get("new_quantity"),
                "change": change,
                "tool": "update_inventory",
            }

        # Name-search path: find product by partial case-insensitive name match
        try:
            inventory = await inv_service.list_inventory(user_id)
        except Exception as exc:
            logger.warning("list_inventory failed for user %s: %s", user_id, exc)
            return {
                "success": False,
                "error": f"Could not retrieve inventory: {exc}",
                "tool": "update_inventory",
            }

        search_term = item.lower()
        matched = next(
            (p for p in inventory if search_term in p.get("name", "").lower()),
            None,
        )
        if matched is None:
            return {
                "success": False,
                "error": (
                    f"Product '{item}' not found in inventory. "
                    "Use list_inventory to see available products."
                ),
                "tool": "update_inventory",
            }

        matched_id = matched["product_id"]
        update_result = await inv_service.update_stock(matched_id, change)
        if "error" in update_result:
            return {
                "success": False,
                "error": update_result["error"],
                "tool": "update_inventory",
            }
        return {
            "success": True,
            "status": "completed",
            "product_id": matched_id,
            "product_name": matched.get("name", item),
            "new_quantity": update_result.get("new_quantity"),
            "change": change,
            "tool": "update_inventory",
        }

    # ------------------------------------------------------------------
    # create_vendor_record
    # ------------------------------------------------------------------

    async def create_vendor_record(
        self,
        user_id: str,
        name: str = "Vendor",
        category: str = "other",
        monthly_cost: float = 0,
        notes: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a vendor record in the vendor_subscriptions table.

        Args:
            user_id: Authenticated user identifier.
            name: Vendor display name.
            category: Vendor category (e.g. "software", "logistics", "other").
            monthly_cost: Estimated monthly cost in USD. Defaults to 0.
            notes: Optional free-text notes. Defaults to a generated note.
            **kwargs: Extra keys like billing_cycle are extracted from kwargs.

        Returns:
            dict with success, status, vendor (row dict), and tool keys.
        """
        row: dict[str, Any] = {
            "user_id": user_id,
            "name": name,
            "category": category,
            "monthly_cost": monthly_cost,
            "billing_cycle": kwargs.get("billing_cycle", "monthly"),
            "notes": notes or "Created via operations workflow",
            "is_active": True,
        }

        try:
            client = _get_service_client()
            result = await execute_async(
                client.table("vendor_subscriptions").insert(row).select(),
                op_name="vendor_ops.create_vendor",
            )
            vendor_row = result.data[0] if result.data else row
            return {
                "success": True,
                "status": "completed",
                "vendor": vendor_row,
                "tool": "create_vendor",
            }
        except Exception as exc:
            logger.exception(
                "create_vendor_record failed for user %s: %s", user_id, exc
            )
            return {
                "success": False,
                "error": f"Failed to create vendor record: {exc}",
                "tool": "create_vendor",
            }

    # ------------------------------------------------------------------
    # create_purchase_order
    # ------------------------------------------------------------------

    async def create_purchase_order(
        self,
        user_id: str,
        vendor: str = "Vendor",
        amount: float | None = None,
        items: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a purchase order reference and create a tracked task.

        The PO reference follows the format ``PO-YYMMDD-NNNN`` where NNNN is a
        random 4-digit number for same-day uniqueness.

        Args:
            user_id: Authenticated user identifier.
            vendor: Vendor name for the purchase order.
            amount: Total PO amount in USD. Optional.
            items: List of line-item dicts (e.g. {sku, qty, unit_price}).
            **kwargs: Ignored — accepted for backward-compat.

        Returns:
            dict with success, status, po_reference, vendor, total_amount, items,
            task (tracking task result), and tool keys.
        """
        now = datetime.now(tz=timezone.utc)
        date_part = now.strftime("%y%m%d")
        random_part = f"{random.randint(0, 9999):04d}"
        po_ref = f"PO-{date_part}-{random_part}"

        task_result = await create_task(
            description=f"Purchase Order {po_ref}: {vendor}"
            + (f" — ${amount:,.2f}" if amount is not None else ""),
        )

        return {
            "success": True,
            "status": "completed",
            "po_reference": po_ref,
            "vendor": vendor,
            "total_amount": amount,
            "items": items or [],
            "task": task_result,
            "tool": "create_po",
        }


# ---------------------------------------------------------------------------
# Module-level wrappers — match the degraded tool call signatures exactly
# so the tool registry can drop-in replace the degraded functions.
# ---------------------------------------------------------------------------


async def update_inventory(
    item: str = "Inventory item",
    quantity: int | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Real inventory update. Replaces the degraded update_inventory stub.

    Resolves user_id from request context. Delegates to
    VendorOpsService.update_inventory_real.

    Args:
        item: Product name or description.
        quantity: Stock change delta. Optional.
        **kwargs: May include product_id for direct-path update.

    Returns:
        dict with success, status="completed", product details, and tool key.
    """
    user_id = get_current_user_id() or "system"
    svc = VendorOpsService()
    return await svc.update_inventory_real(user_id, item, quantity, **kwargs)


async def create_vendor(
    name: str = "Vendor",
    **kwargs: Any,
) -> dict[str, Any]:
    """Real vendor creation. Replaces the degraded create_vendor stub.

    Resolves user_id from request context. Delegates to
    VendorOpsService.create_vendor_record.

    Args:
        name: Vendor display name.
        **kwargs: May include category, monthly_cost, billing_cycle, notes.

    Returns:
        dict with success, status="completed", vendor row, and tool key.
    """
    user_id = get_current_user_id() or "system"
    svc = VendorOpsService()
    return await svc.create_vendor_record(user_id, name, **kwargs)


async def create_po(
    vendor: str = "Vendor",
    amount: float | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Real purchase order creation. Replaces the degraded create_po stub.

    Resolves user_id from request context. Delegates to
    VendorOpsService.create_purchase_order.

    Args:
        vendor: Vendor name for the PO.
        amount: Total PO amount in USD. Optional.
        **kwargs: May include items list.

    Returns:
        dict with success, status="completed", po_reference, and tool key.
    """
    user_id = get_current_user_id() or "system"
    svc = VendorOpsService()
    return await svc.create_purchase_order(user_id, vendor, amount, **kwargs)


__all__ = [
    "VendorOpsService",
    "create_po",
    "create_vendor",
    "update_inventory",
]
