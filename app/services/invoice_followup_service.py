# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Invoice Follow-up Service.

Detects overdue invoices and generates professional follow-up email drafts
for inclusion in the daily briefing (FIN-03).

Usage::

    from app.services.invoice_followup_service import InvoiceFollowupService

    svc = InvoiceFollowupService()
    items = await svc.get_overdue_invoices_with_drafts(user_id)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class InvoiceFollowupService(BaseService):
    """Service for detecting overdue invoices and generating follow-up email drafts.

    Queries the ``invoices`` table for overdue items (status IN ('sent', 'overdue')
    with due_date < today) and produces polite, professional email drafts suitable
    for the morning briefing.
    """

    async def get_overdue_invoices(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch overdue invoices for a user.

        Queries invoices WHERE user_id AND status IN ('sent', 'overdue')
        AND due_date < CURRENT_DATE. Also updates 'sent' invoices to 'overdue'.

        Args:
            user_id: The Supabase user ID.

        Returns:
            List of overdue invoice dicts with id, invoice_number, due_date,
            days_overdue, customer_name, total_amount, and full metadata.
        """
        today = date.today()

        # Query overdue invoices
        response = await execute_async(
            self.client.table("invoices")
            .select("id, invoice_number, due_date, status, metadata")
            .eq("user_id", user_id)
            .in_("status", ["sent", "overdue"])
            .lt("due_date", today.isoformat()),
            op_name="invoice_followup.overdue",
        )

        rows = response.data or []
        result: list[dict[str, Any]] = []

        for row in rows:
            due_date_str = row.get("due_date", "")
            if due_date_str:
                due_dt = date.fromisoformat(due_date_str)
                days_overdue = (today - due_dt).days
            else:
                days_overdue = 0

            metadata = row.get("metadata") or {}

            result.append(
                {
                    "id": row.get("id", ""),
                    "invoice_number": row.get("invoice_number", ""),
                    "due_date": due_date_str,
                    "days_overdue": days_overdue,
                    "customer_name": metadata.get("customer_name", "Unknown"),
                    "customer_email": metadata.get("customer_email", ""),
                    "total_amount": float(metadata.get("total_amount", 0)),
                    "currency": metadata.get("currency", "USD"),
                    "metadata": metadata,
                }
            )

            # Update 'sent' invoices to 'overdue'
            if row.get("status") == "sent":
                try:
                    await execute_async(
                        self.client.table("invoices")
                        .update({"status": "overdue"})
                        .eq("id", row["id"]),
                        op_name="invoice_followup.mark_overdue",
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to update invoice %s status to overdue: %s",
                        row.get("id"),
                        exc,
                    )

        return result

    def generate_followup_draft(self, invoice: dict[str, Any]) -> dict[str, Any]:
        """Generate a polite follow-up email draft for an overdue invoice.

        Args:
            invoice: Invoice dict with id, invoice_number, due_date, metadata.

        Returns:
            Dict with subject, recipient, body, invoice_id, invoice_number,
            days_overdue, and amount.
        """
        metadata = invoice.get("metadata") or {}
        customer_name = metadata.get("customer_name", "Valued Customer")
        customer_email = metadata.get("customer_email", "")
        total_amount = float(metadata.get("total_amount", 0))
        currency = metadata.get("currency", "USD")
        invoice_number = invoice.get("invoice_number", "N/A")
        due_date_str = invoice.get("due_date", "")

        # Compute days overdue
        if due_date_str:
            due_dt = date.fromisoformat(due_date_str)
            days_overdue = (date.today() - due_dt).days
        else:
            days_overdue = 0

        subject = f"Friendly Reminder: Invoice {invoice_number} - Payment Due"
        recipient = customer_email if customer_email else "customer"

        amount_str = f"{total_amount:,.2f}"
        body = (
            f"Hi {customer_name},\n\n"
            f"I hope this message finds you well. I wanted to follow up regarding "
            f"Invoice {invoice_number}, which was due on {due_date_str} "
            f"({days_overdue} days ago).\n\n"
            f"The outstanding amount is {amount_str} {currency}. "
            f"If payment has already been sent, please disregard this message.\n\n"
            f"Please let me know if you have any questions or if there's anything "
            f"I can help with.\n\n"
            f"Best regards"
        )

        return {
            "subject": subject,
            "recipient": recipient,
            "body": body,
            "invoice_id": invoice.get("id", ""),
            "invoice_number": invoice_number,
            "days_overdue": days_overdue,
            "amount": total_amount,
        }

    async def get_overdue_invoices_with_drafts(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        """Get overdue invoices with generated follow-up email drafts.

        Combines overdue invoice detection with email draft generation.

        Args:
            user_id: The Supabase user ID.

        Returns:
            List of dicts combining invoice info and email draft fields.
        """
        overdue = await self.get_overdue_invoices(user_id)
        results: list[dict[str, Any]] = []

        for invoice in overdue:
            draft = self.generate_followup_draft(invoice)
            # Merge invoice info with draft
            combined = {**invoice, **draft}
            results.append(combined)

        return results


def get_overdue_invoices_with_drafts():
    """Module-level convenience reference for the combined method.

    Note: Actual usage should instantiate InvoiceFollowupService
    and call get_overdue_invoices_with_drafts on the instance.
    """
    return InvoiceFollowupService


__all__ = [
    "InvoiceFollowupService",
    "get_overdue_invoices_with_drafts",
]
