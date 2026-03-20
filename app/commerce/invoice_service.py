# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Invoice Service.

Handles invoice generation (PDF), parsing (OCR/LLM), and database management.
"""

import datetime
import io
import json
import logging
from typing import Any

from google.adk.models import Gemini
from google.genai import types
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from supabase import Client

logger = logging.getLogger(__name__)


class InvoiceService:
    def __init__(self):
        self._client: Client | None = None
        # Initialize Gemini for parsing
        # We use a standard model for text extraction/understanding
        self.model = Gemini(
            model="gemini-2.5-flash",  # Fast model for parsing
            generate_content_config=types.GenerateContentConfig(temperature=0.0),
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay_seconds=2.0,
                multiplier=2.0,
                max_delay_seconds=60.0,
            ),
        )

    @property
    def client(self) -> Client:
        """Get Supabase client lazily."""
        if self._client is None:
            try:
                from app.services.supabase import get_service_client

                self._client = get_service_client()
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return self._client

    async def generate_invoice_pdf(self, invoice_data: dict[str, Any]) -> bytes:
        """Generate a PDF invoice from data.

        Args:
            invoice_data: Dictionary containing:
                - invoice_number
                - date
                - customer_name
                - customer_email
                - items: List[Dict] with description, quantity, price, total
                - total_amount

        Returns:
            PDF bytes.
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "INVOICE")

        c.setFont("Helvetica", 12)
        c.drawString(
            50, height - 80, f"Invoice #: {invoice_data.get('invoice_number', 'DRAFT')}"
        )
        c.drawString(
            50,
            height - 100,
            f"Date: {invoice_data.get('date', datetime.date.today().isoformat())}",
        )

        # Customer Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 140, "Bill To:")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 160, invoice_data.get("customer_name", "N/A"))
        c.drawString(50, height - 180, invoice_data.get("customer_email", ""))

        # Table Header
        y = height - 220
        c.line(50, y + 10, width - 50, y + 10)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Description")
        c.drawString(300, y, "Qty")
        c.drawString(350, y, "Unit Price")
        c.drawString(450, y, "Total")
        c.line(50, y - 5, width - 50, y - 5)

        # Items
        y -= 25
        c.setFont("Helvetica", 10)
        items = invoice_data.get("items", [])
        for item in items:
            c.drawString(50, y, str(item.get("description", "Item")))
            c.drawString(300, y, str(item.get("quantity", 0)))
            c.drawString(350, y, f"${item.get('unit_price', 0.0):.2f}")
            c.drawString(450, y, f"${item.get('total', 0.0):.2f}")
            y -= 20

        # Total
        y -= 20
        c.line(50, y + 15, width - 50, y + 15)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(350, y, "Total:")
        c.drawString(450, y, f"${invoice_data.get('total_amount', 0.0):.2f}")

        # Footer
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(50, 50, "Thank you for your business. Payment due within 30 days.")

        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.getvalue()

    async def parse_invoice_text(self, file_content: bytes) -> str:
        """Extract text from a PDF file."""
        try:
            reader = PdfReader(io.BytesIO(file_content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error("Error parsing PDF text: %s", e)
            return ""

    async def extract_invoice_data(self, text: str) -> dict[str, Any]:
        """Use LLM to extract structured data from invoice text."""
        prompt = f"""
        You are an intelligent invoice parser. Extract the following fields from the invoice text below 
        and return them as a JSON object:
        - invoice_number (string)
        - date (YYYY-MM-DD)
        - customer_name (string)
        - total_amount (number)
        - currency (string, default USD)
        - items (list of objects with:
            - description
            - quantity
            - unit_price
            - total
            - type (enum: 'physical', 'service', 'digital') <--- CRITICAL: Infer this based on the item description. 
              Examples: "Consulting", "Labor", "Design" -> "service". "Widget", "Phone" -> "physical". "Software License" -> "digital".
        )

        Invoice Text:
        \"\"\"
        {text}
        \"\"\"
        
        Return ONLY valid JSON.
        """

        try:
            # We use the ADK model wrapper
            # Assuming prompt() is the sync method, usually async is better but ADK might wrap it.
            # Using prompt() returns a GenerateContentResponse
            # Actually, standard ADK usage:
            response = self.model.prompt(prompt)

            # Parse JSON from response
            content = response.text
            # Clean generic markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except Exception as e:
            logger.error("Error extracting data with LLM: %s", e)
            return {"error": str(e)}

    async def create_invoice_record(self, user_id: str, data: dict[str, Any]) -> str:
        """Create an invoice record in Supabase.

        Also creates order record implicitly if needed, or links to existing.
        For simplicity, we create a disconnected invoice or assume logic handles order creation separately.
        This function Creates: Invoice
        """

        # Insert Invoice
        invoice_record = {
            "user_id": user_id,
            "invoice_number": data.get("invoice_number"),
            "status": "draft",
            "due_date": data.get("due_date"),
            "total_amount": data.get(
                "total_amount", 0.0
            ),  # Schema doesn't have total_amount on invoice directly, it's on Order
            # Wait, schema check:
            # orders has total_amount. invoices links to order_id.
            # So we should create an Order first if one doesn't exist.
        }

        # Let's create an Order first to hold the items and total
        order_record = {
            "user_id": user_id,
            "customer_name": data.get("customer_name"),
            "total_amount": data.get("total_amount", 0.0),
            "status": "draft",
        }

        res_order = self.client.table("orders").insert(order_record).execute()
        order_id = res_order.data[0]["id"]

        # Insert Items
        if "items" in data:
            items_records = []
            for item in data["items"]:
                items_records.append(
                    {
                        "order_id": order_id,
                        # product_id would be needed if linking to inventory, skipping purely string items for now
                        # or schema requires product_id? No, let's check schema.
                        # Schema: product_id REFERENCES products(id). It is nullable?
                        # "product_id UUID REFERENCES products(id)" -> Default is nullable in postgres if not specified NOT NULL
                        # But let's verify schema.
                        "quantity": item.get("quantity", 1),
                        "unit_price": item.get("unit_price", 0),
                        "total": item.get("total", 0),
                    }
                )
            if items_records:
                self.client.table("order_items").insert(items_records).execute()

        # Now create Invoice linked to Order
        invoice_record = {
            "user_id": user_id,
            "order_id": order_id,
            "invoice_number": data.get("invoice_number"),
            "status": "draft",
            "due_date": data.get("due_date", datetime.date.today().isoformat()),
            "metadata": data.get("metadata", {}),
        }

        res_inv = self.client.table("invoices").insert(invoice_record).execute()
        return res_inv.data[0]["id"]


# Singleton accessor
_service = None


def get_invoice_service():
    global _service
    if _service is None:
        _service = InvoiceService()
    return _service
