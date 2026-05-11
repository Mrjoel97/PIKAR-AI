# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Background worker that upgrades 'status' outcomes to 'llm' outcomes.

Scans workflow_steps with status='completed' and outcome_text IS NULL, calls
Gemini Flash with a fixed prompt to produce a one-sentence summary, and writes
it back with outcome_source='llm'. Designed to run periodically (e.g. every
few minutes via Cloud Scheduler).
"""

import asyncio
import logging
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

SUMMARY_TIMEOUT_S = 10.0
SUMMARY_MAX_OUTPUT_TOKENS = 80
SUMMARY_MODEL = "gemini-2.5-flash"

SUMMARY_PROMPT_TEMPLATE = (
    "Summarize what this workflow step accomplished in one sentence "
    "(max 25 words, no preamble, no markdown).\n"
    "Tool: {tool}\nOutput: {output}\n\nSummary:"
)


async def _summarize(tool_name: str, output_data: Any) -> str | None:
    """Call Gemini Flash with the summarization prompt.

    Returns the summary text, or None on any failure. Never raises.
    Kept as a module-level function so tests can patch it.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.warning("google.genai not available; cannot summarize")
        return None

    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        tool=tool_name,
        output=str(output_data)[:2000],
    )
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=SUMMARY_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=SUMMARY_MAX_OUTPUT_TOKENS,
                ),
            ),
            timeout=SUMMARY_TIMEOUT_S,
        )
        text = (getattr(response, "text", None) or "").strip()
        return text or None
    except asyncio.TimeoutError:
        logger.warning("LLM summary timed out after %ss", SUMMARY_TIMEOUT_S)
        return None
    except Exception:
        logger.warning("LLM summary call failed", exc_info=True)
        return None


class OutcomeSummaryWorker:
    """Upgrades pending workflow_step outcomes to LLM-synthesized summaries."""

    def __init__(self, client: Any | None = None) -> None:
        """Initialize the worker with an optional Supabase client.

        Args:
            client: Optional pre-constructed Supabase client. If None, the
                service client is fetched lazily on first use.
        """
        self._client = client

    @property
    def client(self) -> Any:
        """Return the Supabase client, creating one if needed."""
        return self._client or get_service_client()

    async def run_once(self, limit: int = 50) -> int:
        """Process one batch of pending outcomes.

        Selects completed workflow steps with no outcome_text, calls
        _summarize for each, and writes the LLM-generated summary back
        with outcome_source='llm'.

        Args:
            limit: Maximum number of steps to process in one pass.

        Returns:
            Number of LLM-upgraded outcomes written.
        """
        select_res = await execute_async(
            self.client.table("workflow_steps")
            .select("id, status, tool_name, output_data, outcome_text, outcome_source")
            .eq("status", "completed")
            .is_("outcome_text", "null"),
            op_name="outcome_summary_worker.scan",
        )
        rows = list((getattr(select_res, "data", None) or []))[:limit]

        upgraded = 0
        for step in rows:
            summary = await _summarize(
                step.get("tool_name") or "unknown",
                step.get("output_data") or {},
            )
            if not summary:
                continue
            try:
                await execute_async(
                    self.client.table("workflow_steps")
                    .update(
                        {
                            "outcome_text": summary[:280],
                            "outcome_source": "llm",
                        }
                    )
                    .eq("id", step["id"]),
                    op_name="outcome_summary_worker.update",
                )
                upgraded += 1
            except Exception:
                logger.warning(
                    "Failed to write LLM outcome for step %s",
                    step["id"],
                    exc_info=True,
                )
        return upgraded
