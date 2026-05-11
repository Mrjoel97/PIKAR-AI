"""Daily cleanup that archives workspace_items for completed workflow runs."""

import logging
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)


async def archive_stale_workflow_items(client: Any | None = None) -> int:
    """Call the archive_stale_workflow_items RPC. Returns number archived.

    Returns 0 on any failure; never raises. Designed for safe invocation from
    a daily scheduler.
    """
    c = client or get_service_client()
    try:
        res = await execute_async(
            c.rpc("archive_stale_workflow_items"),
            op_name="workspace_items_cleanup.archive",
        )
        rows = getattr(res, "data", None) or []
        if not rows:
            return 0
        return int(rows[0].get("archived", 0) or 0)
    except Exception:
        logger.error("archive_stale_workflow_items failed", exc_info=True)
        return 0
