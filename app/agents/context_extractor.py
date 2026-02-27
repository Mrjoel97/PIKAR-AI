# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Context Extractor — ADK callbacks for automatic context memory.

Provides before_model_callback and after_tool_callback that:
1. Inject accumulated user context from session.state into the model prompt
2. Persist facts saved via save_user_context tool to session.state
3. Retrieve saved context when get_conversation_context is called
4. Auto-extract business facts from user messages (safety net)
5. Load cross-session context from Knowledge Vault on new sessions
"""

import json
import logging
import re
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# State key where user context facts are stored
USER_CONTEXT_STATE_KEY = "user_context"

# Flag to avoid repeated RAG lookups within the same session
_CROSS_SESSION_LOADED_KEY = "_cross_session_context_loaded"


def _get_user_context_dict(callback_context: CallbackContext) -> dict:
    """Retrieve the user context dict from session state."""
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
    """Format user context as a readable summary for prompt injection."""
    ctx = _get_user_context_dict(callback_context)
    if not ctx:
        return "No business context saved yet. Pay attention to what the user tells you and use save_user_context to remember key facts."
    lines = []
    for key, value in ctx.items():
        # Format key from snake_case to Title Case
        label = key.replace("_", " ").title()
        lines.append(f"- **{label}**: {value}")
    return "\n".join(lines)


# =============================================
# Auto-extraction patterns (Fix #4 safety net)
# =============================================

# Patterns that detect business-relevant context in user messages
_BUSINESS_PATTERNS = [
    # Brand/company: "my brand X", "my company X", "we're called X", "our brand X"
    (r"(?:my|our|the)\s+(?:brand|company|business|startup|agency|firm|store|shop)\s+(?:is\s+)?(?:called\s+)?[\"']?([A-Z][A-Za-z0-9\s&.-]{1,30})[\"']?", "company_name"),
    # Industry: "in the X industry/space/market"
    (r"(?:in|for)\s+the\s+([a-zA-Z\s&-]{3,25})\s+(?:industry|space|market|sector|niche)", "industry"),
    # Target audience: "targeting X", "audience is X", "for X audience"
    (r"(?:targeting|target(?:ed)?|audience\s+is|aimed?\s+at|for)\s+([A-Za-z0-9\s,-]{3,40})(?:\.|,|$|\s+(?:on|through|via|and))", "target_audience"),
    # Platform: "on TikTok/Instagram/YouTube/LinkedIn/Twitter/X"
    (r"(?:on|for|via|through|across)\s+(TikTok|Instagram|YouTube|LinkedIn|Twitter|Facebook|Snapchat|Pinterest|Reddit|X\b)(?:\s+and\s+(TikTok|Instagram|YouTube|LinkedIn|Twitter|Facebook|Snapchat|Pinterest|Reddit|X\b))?", "platform"),
    # Product: "our product X", "selling X", "launching X"
    (r"(?:our|my|the)\s+(?:product|service|app|tool|platform|solution)\s+(?:is\s+)?(?:called\s+)?[\"']?([A-Z][A-Za-z0-9\s&.-]{1,30})[\"']?", "product_name"),
]

_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), key) for p, key in _BUSINESS_PATTERNS]


def _auto_extract_context(text: str) -> dict[str, str]:
    """Extract obvious business facts from user text using pattern matching.

    This is a lightweight safety net — it catches commonly stated facts
    like brand names, industries, and target audiences without requiring
    the LLM to explicitly call save_user_context.
    """
    extracted = {}
    for pattern, key in _COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip().rstrip(".,;:!?")
            # Skip very short or common-word matches
            if len(value) > 2 and value.lower() not in {"the", "and", "for", "our", "my", "this"}:
                extracted[key] = value
                # For platform, also capture second match if present
                if key == "platform" and match.lastindex and match.lastindex >= 2 and match.group(2):
                    extracted[key] = f"{value}, {match.group(2).strip()}"
    return extracted


def _get_latest_user_text(llm_request: Any) -> str:
    """Extract the most recent user message text from the LLM request."""
    try:
        if hasattr(llm_request, 'contents') and llm_request.contents:
            # Walk backwards to find the latest user message
            for content in reversed(llm_request.contents):
                if hasattr(content, 'role') and content.role == 'user':
                    if hasattr(content, 'parts') and content.parts:
                        texts = [p.text for p in content.parts if hasattr(p, 'text') and p.text]
                        return " ".join(texts)
    except Exception as e:
        logger.debug(f"[ContextMemory] Could not extract user text: {e}")
    return ""


def _try_load_cross_session_context(callback_context: CallbackContext) -> None:
    """Load user context from Knowledge Vault for new sessions (Fix #5).

    On the first turn of a new session (when no user_context exists),
    query the Knowledge Vault for recently saved business context and
    bootstrap session.state with it.
    """
    # Only try once per session
    if callback_context.state.get(_CROSS_SESSION_LOADED_KEY):
        return

    callback_context.state[_CROSS_SESSION_LOADED_KEY] = True

    try:
        from app.rag.search_service import search_knowledge_sync
        from app.rag.knowledge_vault import get_supabase_client
        client = get_supabase_client()
        if not client:
            return

        response = search_knowledge_sync(
            supabase_client=client,
            query="user business context company brand product audience",
            top_k=3,
        )
        results = response.get("results", []) if isinstance(response, dict) else []
        if results:
            # Extract key facts from recent knowledge entries
            cross_session_facts = {}
            for result in results:
                content = result.get("content", "") or result.get("text", "")
                auto_facts = _auto_extract_context(content)
                for k, v in auto_facts.items():
                    if k not in cross_session_facts:
                        cross_session_facts[k] = v

            if cross_session_facts:
                callback_context.state[USER_CONTEXT_STATE_KEY] = cross_session_facts
                logger.info(
                    f"[ContextMemory] Loaded {len(cross_session_facts)} facts from Knowledge Vault "
                    f"for cross-session continuity: {list(cross_session_facts.keys())}"
                )
    except Exception as e:
        logger.debug(f"[ContextMemory] Cross-session load skipped: {e}")


def context_memory_after_tool_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: CallbackContext,
    tool_response: dict,
) -> Optional[dict]:
    """After-tool callback that persists context memory tool saves to session.state.

    This intercepts responses from save_user_context and get_conversation_context
    tools and handles the actual state persistence that those tools cannot do
    directly (since they're plain functions without access to ToolContext).
    """
    if not isinstance(tool_response, dict):
        return None

    # Handle save_user_context
    if tool_response.get("_context_memory_save"):
        key = tool_response.get("key", "")
        value = tool_response.get("value", "")
        if key and value:
            current_ctx = _get_user_context_dict(tool_context)
            current_ctx[key] = value
            tool_context.state[USER_CONTEXT_STATE_KEY] = current_ctx
            logger.info(f"[ContextMemory] Saved: {key} = {value}")
            return {
                "status": "saved",
                "message": f"✓ Remembered: {key} = {value}",
                "total_facts": len(current_ctx),
            }

    # Handle get_conversation_context
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

    return None


def context_memory_before_model_callback(
    callback_context: CallbackContext,
    llm_request: Any,
) -> Optional[genai_types.Content]:
    """Before-model callback that injects user context and auto-extracts facts.

    This callback now does THREE things:
    1. Auto-extracts business facts from the latest user message (Fix #4)
    2. Loads cross-session context from Knowledge Vault on new sessions (Fix #5)
    3. Injects the accumulated context into the system prompt
    """
    # --- Fix #5: Cross-session context loading ---
    ctx = _get_user_context_dict(callback_context)
    if not ctx:
        _try_load_cross_session_context(callback_context)
        ctx = _get_user_context_dict(callback_context)

    # --- Fix #4: Auto-extract from latest user message ---
    user_text = _get_latest_user_text(llm_request)
    if user_text:
        auto_facts = _auto_extract_context(user_text)
        if auto_facts:
            # Merge auto-extracted facts (don't overwrite explicit saves)
            for key, value in auto_facts.items():
                if key not in ctx:
                    ctx[key] = value
                    logger.info(f"[ContextMemory] Auto-extracted: {key} = {value}")
            # Persist the merged context
            if auto_facts:
                callback_context.state[USER_CONTEXT_STATE_KEY] = ctx

    # --- Inject context into prompt ---
    if not ctx:
        return None  # No context yet, skip injection

    ctx_summary = _get_user_context_summary(callback_context)

    # Inject as a system instruction addition via the config
    if hasattr(llm_request, 'config') and llm_request.config:
        existing_si = ""
        if hasattr(llm_request.config, 'system_instruction') and llm_request.config.system_instruction:
            si = llm_request.config.system_instruction
            if isinstance(si, str):
                existing_si = si
            elif hasattr(si, 'parts'):
                existing_si = " ".join(
                    p.text for p in (si.parts or []) if hasattr(p, 'text') and p.text
                )

        context_block = (
            f"\n\n[REMEMBERED USER CONTEXT — use this instead of re-asking]\n"
            f"{ctx_summary}\n"
            f"[END REMEMBERED CONTEXT]\n"
        )

        if existing_si and context_block.strip() not in existing_si:
            llm_request.config.system_instruction = existing_si + context_block

    return None  # Don't replace the user message, just augment the system prompt
