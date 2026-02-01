# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Inventory Service.

Manages products and inventory levels.
"""

import os
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

class InventoryService:
    def __init__(self):
        self.client = self._get_supabase()

    def _get_supabase(self) -> Client:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            from dotenv import load_dotenv
            load_dotenv()
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        return create_client(url, key)

    async def add_product(self, user_id: str, name: str, sku: str, price: float, product_type: str = "physical", initial_quantity: int = 0) -> Dict[str, Any]:
        """Create a product and initialize inventory if physical."""
        
        # 1. Create Product
        prod_data = {
            "user_id": user_id,
            "name": name,
            "sku": sku,
            "price": price,
            "type": product_type
        }
        res_prod = self.client.table("products").insert(prod_data).execute()
        product = res_prod.data[0]
        
        # 2. Create Inventory Record only for Physical Goods
        if product_type == "physical":
            inv_data = {
                "product_id": product["id"],
                "quantity": initial_quantity,
                "location": "default"
            }
            self.client.table("inventory").insert(inv_data).execute()
            product["quantity"] = initial_quantity
        else:
            product["quantity"] = None  # Or "N/A"
        
        return product

    async def list_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        """List all products and their current stock."""
        # Supabase join
        res = self.client.table("products").select("*, inventory(quantity, location)").eq("user_id", user_id).execute()
        
        items = []
        for p in res.data:
            inv = p.get("inventory", [])
            # Sum quantity across locations if multiple, or just take first
            qty = sum(i["quantity"] for i in inv) if inv else 0
            
            items.append({
                "product_id": p["id"],
                "name": p["name"],
                "sku": p["sku"],
                "price": p["price"],
                "type": p.get("type", "physical"),
                "quantity": qty
            })
        return items

    async def update_stock(self, product_id: str, change_amount: int) -> Dict[str, Any]:
        """Update inventory quantity (delta).
        
        Returns success for Service/Digital products without changing stock.
        """
        # Check product type first
        prod_res = self.client.table("products").select("type").eq("id", product_id).limit(1).execute()
        if not prod_res.data:
            return {"error": "Product not found"}
            
        product_type = prod_res.data[0].get("type", "physical")
        
        if product_type != "physical":
             return {"product_id": product_id, "message": f"{product_type} product, no stock tracking needed"}

        # Get current inventory
        res = self.client.table("inventory").select("*").eq("product_id", product_id).limit(1).execute()
        if not res.data:
            return {"error": "Inventory record not found"}
        
        inv = res.data[0]
        new_qty = inv["quantity"] + change_amount
        
        self.client.table("inventory").update({"quantity": new_qty}).eq("id", inv["id"]).execute()
        return {"product_id": product_id, "new_quantity": new_qty}

# Singleton
_service = None
def get_inventory_service():
    global _service
    if _service is None:
        _service = InventoryService()
    return _service
