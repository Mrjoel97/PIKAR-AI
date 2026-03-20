# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Context Extractor - ADK callbacks for automatic context memory and personalization.

Provides before_model_callback and after_tool_callback that:
1. Inject accumulated user context from session.state into the model prompt
2. Persist facts saved via save_user_context tool to session.state
3. Retrieve saved context when get_conversation_context is called
4. Auto-extract business facts from user messages (safety net)
5. Load cross-session context from Knowledge Vault on new sessions
6. Inject persona-aware runtime personalization into every active agent
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types as genai_types

from app.services.telemetry import ToolEvent, get_telemetry_service

logger = logging.getLogger(__name__)

USER_CONTEXT_STATE_KEY = "user_context"
USER_AGENT_PERSONALIZATION_STATE_KEY = "user_agent_personalization"
EXECUTIVE_ROOT_AGENT_NAME = "ExecutiveAgent"

_CROSS_SESSION_LOADED_KEY = "_cross_session_context_loaded"


def _get_callback_user_id(callback_context: CallbackContext) -> str | None:
    try:
        raw_user_id = callback_context.state.get("user_id")
        if raw_user_id:
            return str(raw_user_id)
    except Exception:
        return None
    return None


def _get_user_context_dict(callback_context: CallbackContext) -> dict:
    raw = callback_context.state.get(USER_CONTEXT_STATE_KEY)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _get_user_context_summary(callback_context: CallbackContext) -> str:
    ctx = _get_user_context_dict(callback_context)
    if not ctx:
        return (
            "No business context saved yet. Pay attention to what the user tells you "
            "and use save_user_context to remember key facts."
        )
    lines = []
    for key, value in ctx.items():
        label = key.replace("_", " ").title()
        lines.append(f"- **{label}**: {value}")
    return "\n".join(lines)


def _get_user_personalization_state(callback_context: CallbackContext) -> dict[str, Any]:
    raw = callback_context.state.get(USER_AGENT_PERSONALIZATION_STATE_KEY)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _get_callback_agent_name(callback_context: CallbackContext) -> str:
    raw_agent_name = getattr(callback_context, "agent_name", None)
    return str(raw_agent_name).strip() if raw_agent_name else ""


def _get_runtime_system_prompt_override(personalization: dict[str, Any]) -> str:
    raw_override = personalization.get("system_prompt_override")
    if isinstance(raw_override, str):
        return raw_override.strip()
    return ""


def _should_apply_root_instruction_override(callback_context: CallbackContext) -> bool:
    return _get_callback_agent_name(callback_context) == EXECUTIVE_ROOT_AGENT_NAME


_BUSINESS_PATTERNS = [
    (
        r"(?:my|our|the)\s+(?:brand|company|business|startup|agency|firm|store|shop)\s+(?:is\s+)?(?:called\s+)?[\"']?([A-Z][A-Za-z0-9\s&.-]{1,30})[\"']?",
        "company_name",
    ),
    (r"(?:in|for)\s+the\s+([a-zA-Z\s&-]{3,25})\s+(?:industry|space|market|sector|niche)", "industry"),
    (
        r"(?:targeting|target(?:ed)?|audience\s+is|aimed?\s+at|for)\s+([A-Za-z0-9\s,-]{3,40})(?:\.|,|$|\s+(?:on|through|via|and))",
        "target_audience",
    ),
    (
        r"(?:on|for|via|through|across)\s+(TikTok|Instagram|YouTube|LinkedIn|Twitter|Facebook|Snapchat|Pinterest|Reddit|X\b)(?:\s+and\s+(TikTok|Instagram|YouTube|LinkedIn|Twitter|Facebook|Snapchat|Pinterest|Reddit|X\b))?",
        "platform",
    ),
    (
        r"(?:our|my|the)\s+(?:product|service|app|tool|platform|solution)\s+(?:is\s+)?(?:called\s+)?[\"']?([A-Z][A-Za-z0-9\s&.-]{1,30})[\"']?",
        "product_name",
    ),
]
_COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE), key) for pattern, key in _BUSINESS_PATTERNS]


def _auto_extract_context(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    for pattern, key in _COMPILED_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip().rstrip(".,;:!?")
        if len(value) <= 2 or value.lower() in {"the", "and", "for", "our", "my", "this"}:
            continue
        extracted[key] = value
        if key == "platform" and match.lastindex and match.lastindex >= 2 and match.group(2):
            extracted[key] = f"{value}, {match.group(2).strip()}"
    return extracted


def _get_latest_user_text(llm_request: Any) -> str:
    try:
        if hasattr(llm_request, "contents") and llm_request.contents:
            for content in reversed(llm_request.contents):
                if hasattr(content, "role") and content.role == "user":
                    if hasattr(content, "parts") and content.parts:
                        texts = [part.text for part in content.parts if hasattr(part, "text") and part.text]
                        return " ".join(texts)
    except Exception as exc:
        logger.debug("[ContextMemory] Could not extract user text: %s", exc)
    return ""


def _try_load_cross_session_context(callback_context: CallbackContext) -> None:
    if callback_context.state.get(_CROSS_SESSION_LOADED_KEY):
        return

    callback_context.state[_CROSS_SESSION_LOADED_KEY] = True

    try:
        from app.rag.knowledge_vault import get_supabase_client
        from app.rag.search_service import search_knowledge_sync

        client = get_supabase_client()
        if not client:
            return

        response = search_knowledge_sync(
            supabase_client=client,
            query="user business context company brand product audience",
            top_k=3,
        )
        results = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            return

        cross_session_facts: dict[str, str] = {}
        for result in results:
            content = result.get("content", "") or result.get("text", "")
            auto_facts = _auto_extract_context(content)
            for key, value in auto_facts.items():
                cross_session_facts.setdefault(key, value)

        if cross_session_facts:
            callback_context.state[USER_CONTEXT_STATE_KEY] = cross_session_facts
            logger.info(
                "[ContextMemory] Loaded %s facts from Knowledge Vault for cross-session continuity",
                len(cross_session_facts),
            )
    except Exception as exc:
        logger.debug("[ContextMemory] Cross-session load skipped: %s", exc)


# =============================================================================
# Telemetry Helpers
# =============================================================================

_TELEMETRY_AGENT_START_KEY = "_telemetry_agent_start"


def _record_agent_start(callback_context: CallbackContext, task_summary: str | None = None) -> None:
    """Record agent invocation start time in session state."""
    import time

    agent_name = _get_callback_agent_name(callback_context)
    callback_context.state[_TELEMETRY_AGENT_START_KEY] = {
        "agent_name": agent_name,
        "start_time": time.monotonic(),
        "task_summary": (task_summary or "")[:200],
        "user_id": _get_callback_user_id(callback_context),
    }


async def _record_tool_telemetry(tool: Any, tool_context: CallbackContext, status: str) -> None:
    """Create and record a ToolEvent from a timed tool's metadata."""
    if not getattr(tool, "_is_timed_tool", False):
        return
    service = get_telemetry_service()
    event = ToolEvent(
        tool_name=getattr(tool, "__name__", str(tool)),
        agent_name=_get_callback_agent_name(tool_context),
        user_id=_get_callback_user_id(tool_context),
        session_id=tool_context.state.get("session_id"),
        status=status,
        duration_ms=getattr(tool, "_last_duration_ms", None),
        error_type=getattr(tool, "_last_error", None),
    )
    await service.record_tool_event(event)


def context_memory_after_tool_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: CallbackContext,
    tool_response: dict,
) -> Optional[dict]:
    if not isinstance(tool_response, dict):
        return None

    if tool_response.get("_context_memory_save"):
        key = tool_response.get("key", "")
        value = tool_response.get("value", "")
        if key and value:
            current_ctx = _get_user_context_dict(tool_context)
            current_ctx[key] = value
            tool_context.state[USER_CONTEXT_STATE_KEY] = current_ctx
            logger.info("[ContextMemory] Saved: %s = %s", key, value)
            return {
                "status": "saved",
                "message": f"Remembered: {key} = {value}",
                "total_facts": len(current_ctx),
            }

    if tool_response.get("_context_memory_get"):
        current_ctx = _get_user_context_dict(tool_context)
        if current_ctx:
            return {
                "status": "found",
                "facts": current_ctx,
                "summary": _get_user_context_summary(tool_context),
            }
        return {
            "status": "empty",
            "facts": {},
            "message": "No user context saved yet. Use save_user_context to remember important facts.",
        }

    # --- Telemetry: record tool execution ---
    try:
        tool_status = "error" if getattr(tool, "_last_error", None) else "success"
        import asyncio

        loop = asyncio.get_running_loop()
        loop.create_task(_record_tool_telemetry(tool, tool_context, tool_status))
    except Exception:
        pass  # Telemetry never blocks

    return None


def context_memory_before_model_callback(
    callback_context: CallbackContext,
    llm_request: Any,
) -> Optional[genai_types.Content]:
    # --- Telemetry: record agent start ---
    try:
        latest_text = None
        if llm_request and hasattr(llm_request, "contents") and llm_request.contents:
            for content in reversed(llm_request.contents):
                if hasattr(content, "parts"):
                    for part in content.parts:
                        if hasattr(part, "text") and part.text:
                            latest_text = part.text[:200]
                            break
                if latest_text:
                    break
        _record_agent_start(callback_context, latest_text)
    except Exception:
        pass  # Telemetry never blocks

    ctx = _get_user_context_dict(callback_context)
    if not ctx:
        _try_load_cross_session_context(callback_context)
        ctx = _get_user_context_dict(callback_context)

    user_text = _get_latest_user_text(llm_request)
    if user_text:
        auto_facts = _auto_extract_context(user_text)
        if auto_facts:
            for key, value in auto_facts.items():
                if key not in ctx:
                    ctx[key] = value
                    logger.info("[ContextMemory] Auto-extracted: %s = %s", key, value)
            callback_context.state[USER_CONTEXT_STATE_KEY] = ctx

    personalization = _get_user_personalization_state(callback_context)
    personalization_block = ""
    if personalization:
        try:
            from app.services.user_agent_factory import build_runtime_personalization_block

            personalization_block = build_runtime_personalization_block(
                personalization,
                agent_name=_get_callback_agent_name(callback_context),
            )
        except Exception as exc:
            logger.debug("[ContextMemory] Personalization block skipped: %s", exc)

    if not ctx and not personalization_block:
        return None

    ctx_summary = _get_user_context_summary(callback_context) if ctx else ""

    if hasattr(llm_request, "config") and llm_request.config:
        existing_si = ""
        if hasattr(llm_request.config, "system_instruction") and llm_request.config.system_instruction:
            si = llm_request.config.system_instruction
            if isinstance(si, str):
                existing_si = si
            elif hasattr(si, "parts"):
                existing_si = " ".join(
                    part.text for part in (si.parts or []) if hasattr(part, "text") and part.text
                )

        instruction_blocks: list[str] = []
        if personalization_block:
            instruction_blocks.append(personalization_block)
        if ctx_summary:
            instruction_blocks.append(
                f"\n\n[REMEMBERED USER CONTEXT - use this instead of re-asking]\n{ctx_summary}\n[END REMEMBERED CONTEXT]\n"
            )

        root_instruction_override = _get_runtime_system_prompt_override(personalization)
        if root_instruction_override and _should_apply_root_instruction_override(callback_context):
            llm_request.config.system_instruction = root_instruction_override + "".join(
                block for block in instruction_blocks if block.strip()
            )
            return None

        if existing_si:
            additions = [
                block for block in instruction_blocks if block.strip() and block.strip() not in existing_si
            ]
            if additions:
                llm_request.config.system_instruction = existing_si + "".join(additions)
        elif instruction_blocks:
            llm_request.config.system_instruction = "".join(instruction_blocks).strip()

    return None
