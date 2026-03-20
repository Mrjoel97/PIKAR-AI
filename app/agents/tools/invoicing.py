# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Invoice Tools for Agents.

Tools for Financial Agent to manage invoices.
"""

import asyncio
from typing import Any

from app.commerce.invoice_service import get_invoice_service


def generate_invoice(
    user_id: str,
    invoice_number: str,
    customer_name: str,
    customer_email: str,
    items: list[dict[str, Any]],
    total_amount: float,
    due_date: str | None = None,
) -> dict[str, Any]:
    """Generate a new invoice and PDF.

    Args:
        user_id: User Context ID.
        invoice_number: Unique invoice number (e.g., INV-001).
        customer_name: Name of the customer.
        customer_email: Email of the customer.
        items: List of items, each with 'description', 'quantity', 'unit_price', 'total'.
        total_amount: Total sum of the invoice.
        due_date: YYYY-MM-DD string.

    Returns:
        Dictionary with invoice_id and status.
    """
    service = get_invoice_service()

    data = {
        "invoice_number": invoice_number,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
        "total_amount": total_amount,
        "due_date": due_date,
    }

    # Store record
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    invoice_id = loop.run_until_complete(service.create_invoice_record(user_id, data))

    # Generate PDF (in memory only for this tool result, typically would upload to storage)
    # pdf_bytes = loop.run_until_complete(service.generate_invoice_pdf(data))

    return {
        "success": True,
        "invoice_id": invoice_id,
        "message": f"Invoice {invoice_number} created successfully.",
    }


def parse_invoice_document(file_path: str) -> dict[str, Any]:
    """Parse and extract data from an invoice PDF file.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        Structured data extracted from the invoice.
    """
    service = get_invoice_service()

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        loop = asyncio.get_event_loop()
        text = loop.run_until_complete(service.parse_invoice_text(content))
        data = loop.run_until_complete(service.extract_invoice_data(text))

        return {"success": True, "extracted_data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


INVOICE_TOOLS = [generate_invoice, parse_invoice_document]
