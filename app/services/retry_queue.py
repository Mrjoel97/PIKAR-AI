# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Failed Operation Retry Queue.

Persists workflow step failures for background retry with exponential backoff.
Failed steps are inserted when inline retries are exhausted and later picked up
by ``process_retry_queue`` which re-executes them through StepExecutor.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

# Retry schedule: base delay doubles each attempt (5s, 10s, 20s, 40s, ...)
RETRY_BASE_DELAY_SECONDS = 5
RETRY_BACKOFF_MULTIPLIER = 2.0
DEFAULT_MAX_RETRIES = 3
# Maximum age before a pending operation is considered abandoned
MAX_PENDING_AGE_HOURS = 24


async def enqueue_failed_operation(
    *,
    step_id: str,
    execution_id: str,
    tool_name: str,
    input_data: dict[str, Any],
    step_definition: dict[str, Any],
    error_message: str,
    reason_code: str,
    attempt_count: int = 0,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict[str, Any] | None:
    """Insert a failed operation into the retry queue.

    Returns the created row or None on error.
    """
    next_retry_at = datetime.now(timezone.utc) + timedelta(
        seconds=RETRY_BASE_DELAY_SECONDS
    )

    try:
        client = get_service_client()
        result = (
            client.table("failed_operations")
            .insert(
                {
                    "step_id": step_id,
                    "execution_id": execution_id,
                    "tool_name": tool_name,
                    "input_data": input_data,
                    "step_definition": step_definition,
                    "error_message": error_message,
                    "reason_code": reason_code,
                    "attempt_count": attempt_count,
                    "max_retries": max_retries,
                    "next_retry_at": next_retry_at.isoformat(),
                    "status": "pending",
                }
            )
            .execute()
        )
        row = result.data[0] if result.data else None
        if row:
            logger.info(
                "Enqueued failed operation %s (step=%s, tool=%s) for retry at %s",
                row["id"],
                step_id,
                tool_name,
                next_retry_at.isoformat(),
            )
        return row
    except Exception:
        logger.exception("Failed to enqueue operation for step %s", step_id)
        return None


async def process_retry_queue(*, batch_size: int = 10) -> dict[str, Any]:
    """Process pending failed operations that are due for retry.

    Fetches up to ``batch_size`` operations whose ``next_retry_at`` has passed,
    re-executes them through StepExecutor, and updates their status.

    Returns a summary dict with counts of processed, succeeded, failed, and
    dead-lettered operations.
    """
    # Lazy import to avoid circular dependency (StepExecutor -> retry_queue)
    from app.workflows.step_executor import StepExecutor

    client = get_service_client()
    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("failed_operations")
        .select("*")
        .eq("status", "pending")
        .lte("next_retry_at", now)
        .order("next_retry_at")
        .limit(batch_size)
        .execute()
    )
    ops = result.data or []

    summary: dict[str, Any] = {
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "dead_letter": 0,
    }

    if not ops:
        return summary

    executor = StepExecutor(supabase_client=client)

    for op in ops:
        op_id = op["id"]
        attempt = op["attempt_count"] + 1

        # Mark as processing to prevent double-pickup
        client.table("failed_operations").update(
            {"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", op_id).execute()

        summary["processed"] += 1

        # Reconstruct a step dict compatible with StepExecutor.execute_step
        step = {
            "id": op["step_id"],
            "execution_id": op["execution_id"],
            "tool_name": op["tool_name"],
            "input_data": op.get("input_data") or {},
            "step_definition": op.get("step_definition") or {},
        }

        try:
            result_payload = await executor.execute_step(step)
            succeeded = result_payload.get("_execution_meta", {}).get(
                "verification_status"
            ) != "failed"
        except Exception as exc:
            logger.warning(
                "Retry attempt %d failed for operation %s: %s",
                attempt,
                op_id,
                exc,
            )
            succeeded = False

        if succeeded:
            client.table("failed_operations").update(
                {
                    "status": "completed",
                    "attempt_count": attempt,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", op_id).execute()
            summary["succeeded"] += 1
            logger.info("Retry succeeded for operation %s on attempt %d", op_id, attempt)
        elif attempt >= op["max_retries"]:
            # Exhausted all retries — move to dead letter
            client.table("failed_operations").update(
                {
                    "status": "dead_letter",
                    "attempt_count": attempt,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", op_id).execute()
            summary["dead_letter"] += 1
            logger.warning(
                "Operation %s moved to dead letter after %d attempts", op_id, attempt
            )
        else:
            # Schedule next retry with exponential backoff
            delay = RETRY_BASE_DELAY_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** (attempt - 1))
            next_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            client.table("failed_operations").update(
                {
                    "status": "pending",
                    "attempt_count": attempt,
                    "next_retry_at": next_at.isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", op_id).execute()
            summary["failed"] += 1
            logger.info(
                "Operation %s retry %d failed, next retry at %s",
                op_id,
                attempt,
                next_at.isoformat(),
            )

    return summary


async def get_queue_stats() -> dict[str, Any]:
    """Return counts of operations by status for monitoring."""
    client = get_service_client()
    result = client.table("failed_operations").select("status").execute()
    rows = result.data or []

    stats: dict[str, int] = {"pending": 0, "processing": 0, "completed": 0, "dead_letter": 0}
    for row in rows:
        status = row.get("status", "pending")
        stats[status] = stats.get(status, 0) + 1

    stats["total"] = len(rows)
    return stats
