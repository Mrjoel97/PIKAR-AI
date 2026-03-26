# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

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
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.genai import types as genai_types

from app.services.telemetry import ToolEvent, get_telemetry_service

logger = logging.getLogger(__name__)

USER_CONTEXT_STATE_KEY = "user_context"
USER_AGENT_PERSONALIZATION_STATE_KEY = "user_agent_personalization"
EXECUTIVE_ROOT_AGENT_NAME = "ExecutiveAgent"

_CROSS_SESSION_LOADED_KEY = "_cross_session_context_loaded"
_BRAND_PROFILE_LOADED_KEY = "_brand_profile_loaded"

# Agents that receive Brand DNA injection
_CREATIVE_AGENT_NAMES = {
    "ContentCreationAgent",
    "VideoDirectorAgent",
    "GraphicDesignerAgent",
    "CopywriterAgent",
    "MarketingAgent",
    "CampaignAgent",
    "EmailMarketingAgent",
    "SocialMediaAgent",
    "SEOAgent",
    "AudienceAgent",
    "AdPlatformAgent",
    "ExecutiveAgent",
}


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


def _get_user_personalization_state(
    callback_context: CallbackContext,
) -> dict[str, Any]:
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
    (
        r"(?:in|for)\s+the\s+([a-zA-Z\s&-]{3,25})\s+(?:industry|space|market|sector|niche)",
        "industry",
    ),
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
_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), key) for pattern, key in _BUSINESS_PATTERNS
]


def _auto_extract_context(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    for pattern, key in _COMPILED_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip().rstrip(".,;:!?")
        if len(value) <= 2 or value.lower() in {
            "the",
            "and",
            "for",
            "our",
            "my",
            "this",
        }:
            continue
        extracted[key] = value
        if (
            key == "platform"
            and match.lastindex
            and match.lastindex >= 2
            and match.group(2)
        ):
            extracted[key] = f"{value}, {match.group(2).strip()}"
    return extracted


def _get_latest_user_text(llm_request: Any) -> str:
    try:
        if hasattr(llm_request, "contents") and llm_request.contents:
            for content in reversed(llm_request.contents):
                if hasattr(content, "role") and content.role == "user":
                    if hasattr(content, "parts") and content.parts:
                        texts = [
                            part.text
                            for part in content.parts
                            if hasattr(part, "text") and part.text
                        ]
                        return " ".join(texts)
    except Exception as exc:
        logger.debug("[ContextMemory] Could not extract user text: %s", exc)
    return ""


def _try_load_cross_session_context(callback_context: CallbackContext) -> None:
    if callback_context.state.get(_CROSS_SESSION_LOADED_KEY):
        return

    callback_context.state[_CROSS_SESSION_LOADED_KEY] = True

    try:
        from app.services.supabase_client import get_client
        from app.rag.search_service import search_knowledge_sync

        client = get_client()
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


def _try_load_brand_profile(callback_context: CallbackContext) -> str:
    """Load the user's brand profile from Supabase on first invocation per session.

    Returns the formatted brand DNA block for injection, or empty string if
    no profile exists or loading fails. Caches in session state to avoid
    repeated DB queries.
    """
    if callback_context.state.get(_BRAND_PROFILE_LOADED_KEY):
        # Return cached brand block
        from app.agents.tools.brand_profile import BRAND_PROFILE_STATE_KEY

        cached = callback_context.state.get(BRAND_PROFILE_STATE_KEY)
        if cached and isinstance(cached, str):
            return cached
        return ""

    callback_context.state[_BRAND_PROFILE_LOADED_KEY] = True

    user_id = _get_callback_user_id(callback_context)
    if not user_id:
        return ""

    try:
        from app.agents.tools.brand_profile import (
            BRAND_PROFILE_STATE_KEY,
            format_brand_context_block,
        )

        supabase = None
        try:
            from app.services.supabase import get_service_client

            supabase = get_service_client()
        except (ImportError, ConnectionError):
            return ""

        if not supabase:
            return ""

        # Load default profile, fall back to most recent.
        # NOTE: This is a sync .execute() call in a sync callback. It blocks the
        # event loop on first invocation per session, but the result is cached in
        # callback_context.state for all subsequent calls. ADK does not currently
        # support async before_model callbacks, so this is the best available pattern.
        result = (
            supabase.table("brand_profiles")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_default", True)
            .limit(1)
            .execute()
        )
        if not result.data:
            result = (
                supabase.table("brand_profiles")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

        if not result.data:
            return ""

        profile = result.data[0] if isinstance(result.data, list) else result.data
        brand_block = format_brand_context_block(profile)

        # Cache in session state
        callback_context.state[BRAND_PROFILE_STATE_KEY] = brand_block

        logger.info(
            "[BrandDNA] Loaded brand profile '%s' for user %s",
            profile.get("brand_name", "unnamed"),
            user_id,
        )
        return brand_block

    except Exception as exc:
        logger.debug("[BrandDNA] Brand profile load skipped: %s", exc)
        return ""


# =============================================================================
# Cross-Agent Context Enrichment
# =============================================================================

CROSS_AGENT_CONTEXT_KEY = "agent_recent_outputs"
_MAX_CROSS_AGENT_ENTRIES = 5
_MAX_CONTEXT_AGE_TURNS = 10


def _build_cross_agent_context(callback_context) -> str:
    """Build a context block from recent agent outputs stored in session state.

    Returns an instruction block that can be injected into the system prompt,
    giving the current agent visibility into what other agents recently produced.
    """
    recent = callback_context.state.get(CROSS_AGENT_CONTEXT_KEY, [])
    if not recent:
        return ""

    # Filter to entries within the turn window
    relevant = [e for e in recent if e.get("turns_ago", 999) <= _MAX_CONTEXT_AGE_TURNS]
    if not relevant:
        return ""

    lines = ["\n[CROSS-AGENT CONTEXT — use this, do not re-ask the user]"]
    for entry in relevant[:_MAX_CROSS_AGENT_ENTRIES]:
        agent = entry.get("agent", "Unknown")
        summary = entry.get("summary", "")
        turns = entry.get("turns_ago", 0)
        lines.append(f"- {agent} ({turns} turns ago): {summary}")
    lines.append("[END CROSS-AGENT CONTEXT]\n")
    return "\n".join(lines)


def _record_agent_output(callback_context, agent_name: str, summary: str) -> None:
    """Store a summary of what an agent produced, for cross-agent context.

    Called after a tool produces a substantive result. Stored in session state
    so other agents can see it via _build_cross_agent_context().
    """
    if not agent_name or not summary:
        return

    recent = callback_context.state.get(CROSS_AGENT_CONTEXT_KEY, [])

    # Age existing entries
    for entry in recent:
        entry["turns_ago"] = entry.get("turns_ago", 0) + 1

    # Add new entry at the front
    recent.insert(
        0,
        {
            "agent": agent_name,
            "summary": summary[:500],  # Cap to prevent context bloat
            "turns_ago": 0,
        },
    )

    # Keep only recent entries
    callback_context.state[CROSS_AGENT_CONTEXT_KEY] = recent[:_MAX_CROSS_AGENT_ENTRIES]


# =============================================================================
# Session Action Log — tracks what was done so agents don't re-ask or forget
# =============================================================================

SESSION_ACTION_LOG_KEY = "_session_action_log"
_MAX_ACTION_LOG_ENTRIES = 10

# Tools whose args are especially important to remember for "do that again" requests
_HIGH_VALUE_TOOLS = {
    "create_image",
    "create_video_with_veo",
    "create_social_graphic",
    "create_document",
    "create_report_doc",
    "create_custom_spreadsheet",
    "create_feedback_form",
    "create_custom_form",
    "send_email",
    "send_report_email",
    "create_landing_page",
    "publish_page",
    "create_payment_link",
    "create_checkout",
    "start_workflow",
    "create_calendar_event",
    "deep_research",
    "market_research",
    "competitor_research",
    "use_skill",
    "create_custom_skill",
}


def _record_action(
    tool_context: Any, tool_name: str, args: dict, tool_response: dict
) -> None:
    """Record a tool call with its arguments and key results to the session action log.

    This enables continuity — when a user says "do that again but different,"
    the agent can see exactly what was done before.
    """
    if not tool_name:
        return

    action_log = tool_context.state.get(SESSION_ACTION_LOG_KEY, [])

    # Build a concise action record
    record: dict[str, Any] = {
        "tool": tool_name,
        "agent": _get_callback_agent_name(tool_context),
        "turn": len(action_log),
    }

    # Always capture args for high-value tools; for others, capture key args only
    if tool_name in _HIGH_VALUE_TOOLS:
        # Save all args (truncated) for high-value tools
        safe_args: dict[str, Any] = {}
        for k, v in (args or {}).items():
            if isinstance(v, str):
                safe_args[k] = v[:300]
            elif isinstance(v, (int, float, bool)):
                safe_args[k] = v
            elif isinstance(v, list):
                safe_args[k] = str(v)[:200]
            elif isinstance(v, dict):
                safe_args[k] = json.dumps(v, default=str)[:200]
        record["args"] = safe_args
    else:
        # For regular tools, just capture the first string arg as context
        for _k, v in (args or {}).items():
            if isinstance(v, str) and len(v) > 3:
                record["query"] = v[:200]
                break

    # Capture key result fields
    if isinstance(tool_response, dict):
        for key in (
            "url",
            "id",
            "name",
            "title",
            "prompt",
            "status",
            "message",
            "file_url",
            "media_url",
            "page_url",
        ):
            if tool_response.get(key):
                val = tool_response[key]
                record.setdefault("results", {})[key] = (
                    str(val)[:200] if isinstance(val, str) else val
                )

    action_log.append(record)

    # Keep only recent actions
    tool_context.state[SESSION_ACTION_LOG_KEY] = action_log[-_MAX_ACTION_LOG_ENTRIES:]


def _build_session_action_context(callback_context: Any) -> str:
    """Build a context block showing recent actions taken in this session.

    Injected into the system prompt so agents know what was previously done
    and can reference it for "do that again" or "proceed" type requests.
    """
    action_log = callback_context.state.get(SESSION_ACTION_LOG_KEY, [])
    if not action_log:
        return ""

    lines = [
        "\n[SESSION ACTIONS — what was done in this conversation, use for continuity]"
    ]
    for action in action_log[-_MAX_ACTION_LOG_ENTRIES:]:
        tool = action.get("tool", "unknown")
        agent = action.get("agent", "")
        parts = [f"- {tool}"]
        if agent:
            parts[0] += f" (by {agent})"

        # Show args for high-value tools
        args = action.get("args")
        if args:
            arg_strs = [f"{k}={v!r}" for k, v in args.items()]
            parts.append(f"  Args: {', '.join(arg_strs)}")
        elif action.get("query"):
            parts.append(f"  Query: {action['query']}")

        # Show results
        results = action.get("results")
        if results:
            result_strs = [f"{k}={v}" for k, v in results.items()]
            parts.append(f"  Result: {', '.join(result_strs)}")

        lines.append("\n".join(parts))

    lines.append("[END SESSION ACTIONS]\n")
    return "\n".join(lines)


# =============================================================================
# Telemetry Helpers
# =============================================================================

_TELEMETRY_AGENT_START_KEY = "_telemetry_agent_start"

# Keywords that indicate domain routing
_ROUTING_KEYWORDS = {
    "financial": [
        "revenue",
        "cost",
        "budget",
        "p&l",
        "profit",
        "loss",
        "forecast",
        "cash flow",
        "invoice",
        "financial",
    ],
    "content": [
        "blog",
        "article",
        "video",
        "image",
        "social media",
        "post",
        "content",
        "copy",
        "infographic",
        "graphic",
    ],
    "strategic": [
        "strategy",
        "okr",
        "roadmap",
        "initiative",
        "planning",
        "goal",
        "vision",
        "competitive",
    ],
    "sales": [
        "lead",
        "pipeline",
        "deal",
        "prospect",
        "outreach",
        "crm",
        "sales",
        "conversion",
        "close",
    ],
    "marketing": [
        "campaign",
        "seo",
        "email sequence",
        "landing page",
        "ads",
        "marketing",
        "brand",
        "audience",
    ],
    "operations": [
        "process",
        "sop",
        "runbook",
        "optimization",
        "capacity",
        "vendor",
        "operations",
    ],
    "hr": [
        "hire",
        "recruit",
        "onboard",
        "interview",
        "candidate",
        "employee",
        "performance review",
    ],
    "compliance": [
        "compliance",
        "gdpr",
        "hipaa",
        "sox",
        "audit",
        "risk",
        "legal",
        "contract",
        "nda",
    ],
    "support": [
        "ticket",
        "support",
        "customer issue",
        "escalation",
        "churn",
        "sentiment",
    ],
    "data": [
        "data",
        "analytics",
        "dashboard",
        "sql",
        "chart",
        "metric",
        "trend",
        "anomaly",
        "spreadsheet",
    ],
}


def _extract_routing_signals(text: str) -> list[str]:
    """Extract keyword-based routing signals from user message."""
    if not text:
        return []
    text_lower = text.lower()
    signals = []
    for domain, keywords in _ROUTING_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                signals.append(kw)
                break  # one signal per domain is enough
    return signals


def _record_agent_start(
    callback_context: CallbackContext, task_summary: str | None = None
) -> None:
    """Record agent invocation start time in session state."""
    import json
    import time

    agent_name = _get_callback_agent_name(callback_context)
    user_id = _get_callback_user_id(callback_context)
    summary = (task_summary or "")[:200]

    callback_context.state[_TELEMETRY_AGENT_START_KEY] = {
        "agent_name": agent_name,
        "start_time": time.monotonic(),
        "task_summary": summary,
        "user_id": user_id,
    }

    # Routing transparency: log which agent is being invoked with keyword signals
    if agent_name and agent_name != "ExecutiveAgent":
        routing_signals = _extract_routing_signals(summary)
        routing_log = {
            "level": "INFO",
            "event": "agent_routing_decision",
            "selected_agent": agent_name,
            "user_message_preview": summary,
            "routing_signals": routing_signals,
            "user_id": user_id,
            "timestamp": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
        }
        logger.info(json.dumps(routing_log, default=str))


async def _record_tool_telemetry(
    tool: Any, tool_context: CallbackContext, status: str
) -> None:
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
) -> dict | None:
    if not isinstance(tool_response, dict):
        return None

    # --- Session Action Log: record ALL tool calls for continuity ---
    try:
        tool_name = getattr(tool, "__name__", None) or str(tool)
        _record_action(tool_context, tool_name, args, tool_response)
    except Exception:
        pass  # Never blocks

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
        task = loop.create_task(_record_tool_telemetry(tool, tool_context, tool_status))
        # Suppress unhandled exception warnings on the fire-and-forget task
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    except Exception:
        pass  # Telemetry never blocks

    # --- Cross-agent context: record agent output summary ---
    try:
        agent_name = _get_callback_agent_name(tool_context)
        if agent_name and tool_response and isinstance(tool_response, dict):
            # Extract a brief summary from the tool response
            summary_parts = []
            for key in ("summary", "result", "message", "status", "data"):
                if tool_response.get(key):
                    val = tool_response[key]
                    if isinstance(val, str):
                        summary_parts.append(f"{key}: {val[:100]}")
                    elif isinstance(val, dict):
                        summary_parts.append(
                            f"{key}: {json.dumps(val, default=str)[:100]}"
                        )
            if summary_parts:
                _record_agent_output(tool_context, agent_name, "; ".join(summary_parts))
    except Exception:
        pass  # Never blocks

    return None


def context_memory_before_model_callback(
    callback_context: CallbackContext,
    llm_request: Any,
) -> genai_types.Content | None:
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
            from app.services.user_agent_factory import (
                build_runtime_personalization_block,
            )

            personalization_block = build_runtime_personalization_block(
                personalization,
                agent_name=_get_callback_agent_name(callback_context),
            )
        except Exception as exc:
            logger.debug("[ContextMemory] Personalization block skipped: %s", exc)

    # --- Brand DNA: inject brand profile for creative agents ---
    brand_dna_block = ""
    try:
        agent_name = _get_callback_agent_name(callback_context)
        if agent_name in _CREATIVE_AGENT_NAMES:
            brand_dna_block = _try_load_brand_profile(callback_context)
    except Exception:
        pass  # Brand DNA is optional, never blocks

    has_cross_agent = bool(callback_context.state.get(CROSS_AGENT_CONTEXT_KEY))
    has_action_log = bool(callback_context.state.get(SESSION_ACTION_LOG_KEY))
    if (
        not ctx
        and not personalization_block
        and not brand_dna_block
        and not has_cross_agent
        and not has_action_log
    ):
        return None

    ctx_summary = _get_user_context_summary(callback_context) if ctx else ""

    if hasattr(llm_request, "config") and llm_request.config:
        existing_si = ""
        if (
            hasattr(llm_request.config, "system_instruction")
            and llm_request.config.system_instruction
        ):
            si = llm_request.config.system_instruction
            if isinstance(si, str):
                existing_si = si
            elif hasattr(si, "parts"):
                existing_si = " ".join(
                    part.text
                    for part in (si.parts or [])
                    if hasattr(part, "text") and part.text
                )

        instruction_blocks: list[str] = []
        if personalization_block:
            instruction_blocks.append(personalization_block)
        if brand_dna_block:
            instruction_blocks.append(brand_dna_block)
        if ctx_summary:
            context_block = f"\n\n[REMEMBERED USER CONTEXT - use this instead of re-asking]\n{ctx_summary}\n[END REMEMBERED CONTEXT]\n"
            # --- Cross-agent context enrichment ---
            try:
                cross_agent_ctx = _build_cross_agent_context(callback_context)
                if cross_agent_ctx:
                    context_block += cross_agent_ctx
            except Exception:
                pass  # Cross-agent context is optional, never blocks
            # --- Session action log ---
            try:
                action_ctx = _build_session_action_context(callback_context)
                if action_ctx:
                    context_block += action_ctx
            except Exception:
                pass  # Never blocks
            instruction_blocks.append(context_block)
        else:
            # Still inject cross-agent context even when there's no user context summary
            try:
                cross_agent_ctx = _build_cross_agent_context(callback_context)
                if cross_agent_ctx:
                    instruction_blocks.append(cross_agent_ctx)
            except Exception:
                pass  # Cross-agent context is optional, never blocks
            # --- Session action log ---
            try:
                action_ctx = _build_session_action_context(callback_context)
                if action_ctx:
                    instruction_blocks.append(action_ctx)
            except Exception:
                pass  # Never blocks

        root_instruction_override = _get_runtime_system_prompt_override(personalization)
        if root_instruction_override and _should_apply_root_instruction_override(
            callback_context
        ):
            llm_request.config.system_instruction = root_instruction_override + "".join(
                block for block in instruction_blocks if block.strip()
            )
            return None

        if existing_si:
            additions = [
                block
                for block in instruction_blocks
                if block.strip() and block.strip() not in existing_si
            ]
            if additions:
                llm_request.config.system_instruction = existing_si + "".join(additions)
        elif instruction_blocks:
            llm_request.config.system_instruction = "".join(instruction_blocks).strip()

    return None
