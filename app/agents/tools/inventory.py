# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Inventory Tools for Agents.

Tools for Operations Agent to manage stock.
"""

import asyncio
from typing import Any

from app.commerce.inventory_service import get_inventory_service


def add_inventory_item(
    user_id: str,
    name: str,
    sku: str,
    price: float,
    product_type: str = "physical",
    quantity: int = 0,
) -> dict[str, Any]:
    """Add a new product to inventory.

    Args:
        user_id: User context ID.
        name: Product name.
        sku: Stock Keeping Unit identifier.
        price: Unit price.
        product_type: Type of product ('physical', 'service', 'digital').
        quantity: Initial stock count (only for physical).
    """
    service = get_inventory_service()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        service.add_product(user_id, name, sku, price, product_type, quantity)
    )


def list_inventory(user_id: str) -> list[dict[str, Any]]:
    """List all inventory items and stock levels."""
    service = get_inventory_service()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(service.list_inventory(user_id))


def update_inventory_quantity(product_id: str, change: int) -> dict[str, Any]:
    """Update stock level for a product.

    Args:
        product_id: UUID of the product.
        change: Amount to add (positive) or remove (negative).
    """
    service = get_inventory_service()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(service.update_stock(product_id, change))


INVENTORY_TOOLS = [add_inventory_item, list_inventory, update_inventory_quantity]
