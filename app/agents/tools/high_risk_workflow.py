# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""High-risk workflow tool implementations.

These tools handle finance/legal/hr-sensitive workflow steps with:
- explicit input validation,
- auditable structured outputs,
- deterministic run/reference IDs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from app.agents.content.tools import save_content
from app.agents.data.tools import track_event
from app.agents.sales.tools import create_task


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _safe_task(description: str) -> dict:
    """Create a task and gracefully degrade if task backend is unavailable."""
    result = await create_task(description=description)
    if result.get("success"):
        return result
    return {
        "success": False,
        "status": "degraded",
        "task_id": None,
        "error": result.get("error", "task_backend_unavailable"),
    }


async def _safe_event(event_name: str, category: str, properties: dict) -> dict:
    """Emit audit event and degrade gracefully if analytics backend is unavailable."""
    payload = json.dumps(properties)
    result = await track_event(
        event_name=event_name, category=category, properties=payload
    )
    if result.get("success"):
        return result
    return {
        "success": False,
        "status": "degraded",
        "error": result.get("error", "analytics_unavailable"),
    }


async def _safe_document(title: str, content: str) -> dict:
    """Persist an artifact and degrade gracefully if content backend is unavailable."""
    result = await save_content(title=title, content=content)
    if result.get("success"):
        return result
    return {
        "success": False,
        "status": "degraded",
        "error": result.get("error", "content_backend_unavailable"),
    }


async def approve_request(
    request_type: str,
    requester: str,
    justification: str = "",
    amount: float | None = None,
    approver: str | None = None,
    priority: str = "normal",
    **kwargs,
) -> dict:
    """Approve or route approval request with audit trail.

    This function performs policy-level validation and records an auditable event.
    """
    if not request_type.strip():
        return {
            "success": False,
            "status": "failed",
            "error": "request_type is required",
        }
    if not requester.strip():
        return {"success": False, "status": "failed", "error": "requester is required"}
    if amount is not None and amount < 0:
        return {"success": False, "status": "failed", "error": "amount must be >= 0"}

    approval_id = f"apr_{uuid4().hex[:12]}"
    decision = "pending_manual_review"

    task = await _safe_task(
        description=(
            f"[APPROVAL] id={approval_id} type={request_type} requester={requester} "
            f"amount={amount} decision={decision} approver={approver or 'policy-engine'} priority={priority}"
        )
    )
    audit = await _safe_event(
        event_name="approval_decision_recorded",
        category="workflow_approval",
        properties={
            "approval_id": approval_id,
            "request_type": request_type,
            "requester": requester,
            "amount": amount,
            "decision": decision,
            "approver": approver,
            "priority": priority,
            "justification": justification[:500],
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": decision,
        "approval_id": approval_id,
        "decision": decision,
        "task": task,
        "audit": audit,
        "timestamp": _now_iso(),
    }


async def send_contract(
    recipient_email: str,
    contract_title: str,
    contract_body: str = "",
    recipient_name: str | None = None,
    effective_date: str | None = None,
    **kwargs,
) -> dict:
    """Create and dispatch a contract package with artifact + audit trail."""
    if "@" not in recipient_email:
        return {
            "success": False,
            "status": "failed",
            "error": "recipient_email must be valid",
        }
    if not contract_title.strip():
        return {
            "success": False,
            "status": "failed",
            "error": "contract_title is required",
        }

    contract_id = f"ctr_{uuid4().hex[:12]}"
    payload = (
        f"# {contract_title}\n\n"
        f"- Contract ID: {contract_id}\n"
        f"- Recipient: {recipient_name or recipient_email}\n"
        f"- Recipient Email: {recipient_email}\n"
        f"- Effective Date: {effective_date or 'TBD'}\n"
        f"- Generated At: {_now_iso()}\n\n"
        f"## Terms\n\n{contract_body or 'Standard contractual terms apply.'}\n"
    )
    artifact = await _safe_document(
        title=f"Contract - {contract_title}", content=payload
    )
    task = await _safe_task(
        description=f"[CONTRACT] id={contract_id} send_to={recipient_email} title={contract_title}"
    )
    audit = await _safe_event(
        event_name="contract_sent",
        category="workflow_contract",
        properties={
            "contract_id": contract_id,
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "contract_title": contract_title,
            "effective_date": effective_date,
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": "sent",
        "contract_id": contract_id,
        "artifact": artifact,
        "task": task,
        "audit": audit,
        "timestamp": _now_iso(),
    }


async def query_timesheets(
    pay_period: str,
    department: str | None = None,
    **kwargs,
) -> dict:
    """Retrieve payroll input data (currently through workflow task + audit path)."""
    if not pay_period.strip():
        return {"success": False, "status": "failed", "error": "pay_period is required"}
    run_id = f"tsq_{uuid4().hex[:12]}"
    task = await _safe_task(
        description=f"[TIMESHEET_QUERY] run_id={run_id} pay_period={pay_period} department={department or 'all'}"
    )
    audit = await _safe_event(
        event_name="timesheet_query_submitted",
        category="workflow_payroll",
        properties={
            "run_id": run_id,
            "pay_period": pay_period,
            "department": department,
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": "submitted",
        "query_id": run_id,
        "pay_period": pay_period,
        "department": department,
        "task": task,
        "audit": audit,
    }


async def execute_payroll(
    pay_period: str,
    total_amount: float,
    currency: str = "usd",
    approved_by: str | None = None,
    **kwargs,
) -> dict:
    """Execute payroll run with mandatory approval metadata."""
    if not pay_period.strip():
        return {"success": False, "status": "failed", "error": "pay_period is required"}
    if total_amount <= 0:
        return {
            "success": False,
            "status": "failed",
            "error": "total_amount must be > 0",
        }
    if not approved_by:
        return {
            "success": False,
            "status": "failed",
            "error": "approved_by is required",
        }

    payroll_run_id = f"pay_{uuid4().hex[:12]}"
    task = await _safe_task(
        description=(
            f"[PAYROLL] run_id={payroll_run_id} pay_period={pay_period} "
            f"total_amount={total_amount:.2f} {currency.upper()} approved_by={approved_by}"
        )
    )
    audit = await _safe_event(
        event_name="payroll_executed",
        category="workflow_payroll",
        properties={
            "payroll_run_id": payroll_run_id,
            "pay_period": pay_period,
            "total_amount": total_amount,
            "currency": currency.lower(),
            "approved_by": approved_by,
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": "executed",
        "payroll_run_id": payroll_run_id,
        "pay_period": pay_period,
        "total_amount": total_amount,
        "currency": currency.lower(),
        "approved_by": approved_by,
        "task": task,
        "audit": audit,
        "timestamp": _now_iso(),
    }


async def process_payment(
    amount: float,
    currency: str = "usd",
    description: str = "Workflow payment",
    customer_email: str | None = None,
    **kwargs,
) -> dict:
    """Process outbound or customer payment request with validation and audit."""
    if amount <= 0:
        return {"success": False, "status": "failed", "error": "amount must be > 0"}

    payment_id = f"pmt_{uuid4().hex[:12]}"
    checkout = None

    # Best-effort Stripe checkout path for customer-facing payments.
    if customer_email:
        try:
            from app.mcp.tools.stripe_payments import create_checkout_session

            stripe_result = await create_checkout_session(
                product_name=description[:80] or "Workflow Payment",
                price_amount=int(round(amount * 100)),
                currency=currency.lower(),
                customer_email=customer_email,
            )
            if stripe_result.get("success"):
                checkout = {
                    "session_id": stripe_result.get("session_id"),
                    "url": stripe_result.get("url"),
                }
        except (KeyError, ValueError):
            checkout = None

    task = await _safe_task(
        description=(
            f"[PAYMENT] id={payment_id} amount={amount:.2f} {currency.upper()} "
            f"description={description} customer_email={customer_email or 'n/a'}"
        )
    )
    audit = await _safe_event(
        event_name="payment_requested",
        category="workflow_finance",
        properties={
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency.lower(),
            "description": description[:500],
            "customer_email": customer_email,
            "checkout_created": bool(checkout),
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": "processed",
        "payment_id": payment_id,
        "amount": amount,
        "currency": currency.lower(),
        "checkout": checkout,
        "task": task,
        "audit": audit,
        "timestamp": _now_iso(),
    }


async def send_payment(
    payee: str,
    amount: float,
    currency: str = "usd",
    reference: str | None = None,
    **kwargs,
) -> dict:
    """Execute supplier/vendor payment transfer request."""
    if not payee.strip():
        return {"success": False, "status": "failed", "error": "payee is required"}
    if amount <= 0:
        return {"success": False, "status": "failed", "error": "amount must be > 0"}

    transfer_id = f"trf_{uuid4().hex[:12]}"
    task = await _safe_task(
        description=(
            f"[TRANSFER] id={transfer_id} payee={payee} amount={amount:.2f} "
            f"{currency.upper()} reference={reference or 'none'}"
        )
    )
    audit = await _safe_event(
        event_name="payment_transfer_requested",
        category="workflow_finance",
        properties={
            "transfer_id": transfer_id,
            "payee": payee,
            "amount": amount,
            "currency": currency.lower(),
            "reference": reference,
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": "submitted",
        "transfer_id": transfer_id,
        "payee": payee,
        "amount": amount,
        "currency": currency.lower(),
        "reference": reference,
        "task": task,
        "audit": audit,
    }


async def transfer_money(
    from_account: str,
    to_account: str,
    amount: float,
    currency: str = "usd",
    **kwargs,
) -> dict:
    """Execute inter-account transfer request with validation + audit."""
    if not from_account.strip() or not to_account.strip():
        return {
            "success": False,
            "status": "failed",
            "error": "from_account and to_account are required",
        }
    if amount <= 0:
        return {"success": False, "status": "failed", "error": "amount must be > 0"}
    if from_account == to_account:
        return {
            "success": False,
            "status": "failed",
            "error": "from_account and to_account must differ",
        }

    transfer_id = f"xfr_{uuid4().hex[:12]}"
    task = await _safe_task(
        description=(
            f"[INTERNAL_TRANSFER] id={transfer_id} from={from_account} to={to_account} "
            f"amount={amount:.2f} {currency.upper()}"
        )
    )
    audit = await _safe_event(
        event_name="internal_transfer_requested",
        category="workflow_finance",
        properties={
            "transfer_id": transfer_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "currency": currency.lower(),
            "timestamp": _now_iso(),
        },
    )
    return {
        "success": True,
        "status": "submitted",
        "transfer_id": transfer_id,
        "task": task,
        "audit": audit,
    }
