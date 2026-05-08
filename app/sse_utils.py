# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""SSE (Server-Sent Events) utilities for the FastAPI application.

This module contains:
- Widget extraction from ADK events
- Reasoning trace extraction (tool calls, tool results, agent delegation)
- Synthetic text injection for widgets
- Progress event serialization
- Model error detection for fallback handling
"""

import json
import logging
import re
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Mirror of frontend `workspaceArtifacts.ts` thresholds (Wave 1 lowered them).
# Plain prose ≥ this length always promotes to a markdown_report widget.
LONGFORM_MIN_CHARS = 200
# Structured markdown (headings, lists, fences, tables) promotes earlier.
STRUCTURED_MIN_CHARS = 140
# Or 12+ non-empty lines (matches frontend nonEmptyLineCount rule).
LONGFORM_MIN_LINES = 12
_TITLE_MAX_LENGTH = 88
_MARKDOWN_TITLE_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_MARKDOWN_SIGNAL_RE = re.compile(
    r"(^|\n)\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|\|.+\||```)"
)
_MARKDOWN_STRIP_RE = re.compile(r"[*_`~]")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_HEADING_PREFIX_RE = re.compile(r"^#{1,6}\s+")

# Widget types that the UI can render (must match frontend WidgetRegistry)
RENDERABLE_WIDGET_TYPES = {
    "initiative_dashboard",
    "revenue_chart",
    "product_launch",
    "kanban_board",
    "workflow_builder",
    "morning_briefing",
    "boardroom",
    "suggested_workflows",
    "form",
    "table",
    "calendar",
    "workflow",
    "image",
    "video",
    "video_spec",
    "braindump_analysis",
    "markdown_report",
    "campaign_hub",
    "self_improvement",
    "workflow_observability",
    "workflow_timeline",
    "daily_briefing",
    "landing_pages",
    "api_connections",
    "department_activity",
    "document",
    "app_builder_launcher",
    "app_builder_canvas",
    "director_storyboard",
    "approval",
}


def is_model_unavailable_error(e: Exception) -> bool:
    """Check if the error indicates the primary model is unavailable.

    Uses exception type checking when possible, with string matching as fallback.
    Handles:
    - HTTP 404: Model not found
    - HTTP 429: Rate limit exceeded
    - RESOURCE_EXHAUSTED: Quota exceeded
    - Model-specific unavailability errors

    Args:
        e: The exception to check.

    Returns:
        True if the error indicates model unavailability, False otherwise.
    """
    # Check for specific exception types from google.genai/google.api_core
    exc_type = type(e).__name__
    exc_module = type(e).__module__

    # Google API core exceptions
    if "google.api_core" in exc_module:
        # NotFound (404), ResourceExhausted (429), ServiceUnavailable
        if exc_type in ("NotFound", "ResourceExhausted", "ServiceUnavailable"):
            return True

    # Google genai exceptions
    if "google.genai" in exc_module:
        if exc_type in (
            "NotFoundError",
            "ResourceExhaustedError",
            "InvalidArgumentError",
        ):
            return True

    # Fallback to string matching for wrapped/serialized errors
    msg = (str(e) or "").upper()
    return (
        "404" in msg
        or "429" in msg
        or "RESOURCE_EXHAUSTED" in msg
        or "NOT_FOUND" in msg
        or (
            "MODEL" in msg
            and ("UNAVAILABLE" in msg or "NOT FOUND" in msg or "INVALID" in msg)
        )
    )


def _normalize_markdown(text: str) -> str:
    """Normalize line endings and strip outer whitespace for markdown checks."""
    return text.replace("\r\n", "\n").strip() if text else ""


def _strip_markdown_for_title(value: str) -> str:
    """Flatten markdown formatting characters out of a candidate title string."""
    out = _MARKDOWN_HEADING_PREFIX_RE.sub("", value)
    out = _MARKDOWN_LINK_RE.sub(r"\1", out)
    out = _MARKDOWN_STRIP_RE.sub("", out)
    return re.sub(r"\s+", " ", out).strip()


def _truncate(text: str, max_length: int) -> str:
    """Truncate to *max_length* with an ellipsis if the source is longer."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _derive_markdown_title(markdown: str, agent_name: str | None) -> str:
    """Pick a title: first heading → first non-empty stripped line → fallback."""
    heading = _MARKDOWN_TITLE_RE.search(markdown)
    if heading and heading.group(1):
        return _truncate(_strip_markdown_for_title(heading.group(1)), _TITLE_MAX_LENGTH)
    for raw_line in markdown.split("\n"):
        cleaned = _strip_markdown_for_title(raw_line)
        if cleaned:
            return _truncate(cleaned, _TITLE_MAX_LENGTH)
    fallback = f"{agent_name} report" if agent_name else "Agent report"
    return _truncate(fallback, _TITLE_MAX_LENGTH)


def _qualifies_as_markdown_report(markdown: str) -> bool:
    """Return True when the accumulated text passes any longform threshold."""
    if not markdown:
        return False
    if len(markdown) >= LONGFORM_MIN_CHARS:
        return True
    has_structured = bool(_MARKDOWN_SIGNAL_RE.search(markdown))
    if has_structured and len(markdown) >= STRUCTURED_MIN_CHARS:
        return True
    non_empty_lines = sum(1 for line in markdown.split("\n") if line.strip())
    return non_empty_lines >= LONGFORM_MIN_LINES


def _synthesize_markdown_report_widget(
    accumulated_text: str,
    *,
    session_id: str | None,
    user_id: str | None,
    agent_name: str | None = None,
) -> dict[str, Any] | None:
    """Promote a longform agent reply to a `markdown_report` widget envelope.

    Mirrors the frontend `buildMarkdownWorkspaceWidget` heuristics so the
    backend becomes the primary writer for durable longform deliverables.
    The widget is best-effort persisted via `persist_chat_widget` (any
    failure is swallowed and logged at WARNING).

    Args:
        accumulated_text: Concatenated agent text from the SSE stream.
        session_id: Caller-provided chat session id (may be None).
        user_id: Owning user id; persistence is skipped when missing.
        agent_name: Author of the reply, used as a title fallback.

    Returns:
        A `markdown_report` widget dict or None if thresholds aren't met.
    """
    markdown = _normalize_markdown(accumulated_text)
    if not _qualifies_as_markdown_report(markdown):
        return None

    title = _derive_markdown_title(markdown, agent_name)
    widget: dict[str, Any] = {
        "type": "markdown_report",
        "title": title,
        "data": {
            "markdown": markdown,
            "title": title,
            "agentName": agent_name,
            "kind": "report",
        },
        "widget_id": str(uuid.uuid4()),
        "workspace": {
            "workspaceItemId": str(uuid.uuid4()),
            "mode": "focus",
            "sessionId": session_id,
        },
    }

    # Best-effort persistence — never raise back into the SSE generator.
    try:
        from app.services.chat_widget_persistence import persist_chat_widget

        persist_chat_widget(
            user_id=user_id,
            widget=widget,
            session_id=session_id,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort persistence
        logger.warning(
            "markdown_report widget persistence failed: %s", exc
        )

    return widget


def _extract_widget_candidate(payload: Any) -> dict[str, Any] | None:
    """Return a renderable widget from a tool payload or wrapper object."""
    if not isinstance(payload, dict):
        return None

    if payload.get("type") in RENDERABLE_WIDGET_TYPES and isinstance(
        payload.get("data"), dict
    ):
        return payload

    widget = payload.get("widget")
    if isinstance(widget, dict) and widget.get("type") in RENDERABLE_WIDGET_TYPES:
        if isinstance(widget.get("data"), dict):
            return widget

    result = payload.get("result")
    if isinstance(result, dict):
        return _extract_widget_candidate(result)

    return None


def inject_synthetic_text_for_widget(
    event_data: dict, widget_def: dict, parts: list
) -> None:
    """Ensure content.parts has at least one text part so the UI never shows a blank response.

    Uses user_message (errors), widget caption/title, or a short default by type.

    Args:
        event_data: The event data dictionary to modify.
        widget_def: The widget definition containing type, title, etc.
        parts: The list of content parts to check/modify.
    """
    content = event_data.get("content") or {}
    if not isinstance(content, dict):
        return
    has_text = any(isinstance(p, dict) and p.get("text") for p in parts)
    if has_text:
        return
    # Prefer tool-provided user_message (e.g. error or status), then caption/title, then default
    synthetic = (
        widget_def.get("user_message")
        or (
            isinstance(widget_def.get("data"), dict)
            and widget_def["data"].get("caption")
        )
        or widget_def.get("title")
    )
    if not synthetic or not synthetic.strip():
        wtype = widget_def.get("type") or ""
        if wtype == "video" or wtype == "video_spec":
            synthetic = "Here's your video. You can play it below and find it in Knowledge Vault → Media."
        elif wtype == "image":
            synthetic = "Here's your image. You can view it below and find it in Knowledge Vault → Media."
        else:
            synthetic = "Here's what I created for you."
    parts_list = list(parts)
    parts_list.append({"text": synthetic.strip()})
    event_data["content"] = {**content, "parts": parts_list}


def inject_synthetic_text_for_tool_message(
    event_data: dict, text: str, parts: list
) -> None:
    """Inject a single text part when the tool returned a message (e.g. error) but no widget.

    Args:
        event_data: The event data dictionary to modify.
        text: The text to inject.
        parts: The list of content parts to check/modify.
    """
    content = event_data.get("content") or {}
    if not isinstance(content, dict):
        return
    has_text = any(isinstance(p, dict) and p.get("text") for p in parts)
    if has_text:
        return
    parts_list = list(parts)
    parts_list.append({"text": text})
    event_data["content"] = {**content, "parts": parts_list}


def extract_widget_from_event(event_json: str) -> str:
    """Post-process an SSE event to extract widget definitions from tool results.

    When the agent calls a widget tool, the tool returns a dict like:
      {"type": "revenue_chart", "title": "...", "data": {...}, "dismissible": true}

    ADK serializes this as text in the event's content parts. This function
    detects such patterns and injects a top-level 'widget' field into the
    event JSON so the frontend can render the widget.

    Args:
        event_json: The JSON string of the serialized ADK event.

    Returns:
        Modified JSON string with 'widget' field injected, or original if no widget found.
    """
    try:
        event_data = json.loads(event_json)
    except (json.JSONDecodeError, TypeError):
        return event_json

    # Already has a widget field - pass through
    if event_data.get("widget"):
        return event_json

    # Check content.parts for widget definitions embedded in text
    content = event_data.get("content")
    if not content or not isinstance(content, dict):
        return event_json

    parts = content.get("parts") or []

    for part in parts:
        if not isinstance(part, dict):
            continue
        # Check for function_response (tool result) - support both snake_case and camelCase
        func_response = part.get("function_response") or part.get("functionResponse")
        if func_response:
            response_data = (
                func_response.get("response")
                or func_response.get("response_data")
                or {}
            )
            if not isinstance(response_data, dict):
                response_data = {}

            # Check for top-level error in functionResponse (ADK crash/exception)
            # This happens when the tool raises an exception that ADK catches and reports.
            top_level_error = func_response.get("error")
            if top_level_error:
                inject_synthetic_text_for_tool_message(
                    event_data, f"Tool Execution Error: {top_level_error!s}", parts
                )
                return json.dumps(event_data)

            # Check for tool failure FIRST — if the tool explicitly reported
            # failure, skip widget extraction and only inject the error message.
            # This prevents synthetic "Here's your video" text on failed attempts.
            is_failure = response_data.get("success") is False
            user_message = response_data.get("user_message") or response_data.get(
                "userMessage"
            )
            if is_failure:
                if (
                    user_message
                    and isinstance(user_message, str)
                    and user_message.strip()
                ):
                    inject_synthetic_text_for_tool_message(
                        event_data, user_message.strip(), parts
                    )
                    return json.dumps(event_data)
                err_msg = response_data.get("error")
                if err_msg and isinstance(err_msg, str) and err_msg.strip():
                    inject_synthetic_text_for_tool_message(
                        event_data, err_msg.strip(), parts
                    )
                    return json.dumps(event_data)
                # Generic failure — don't inject success text
                continue

            widget_def = _extract_widget_candidate(response_data)
            if widget_def:
                event_data["widget"] = widget_def
                logger.info(
                    f"[SSE] Extracted widget from tool result: type={widget_def['type']}"
                )
                inject_synthetic_text_for_widget(event_data, widget_def, parts)
                return json.dumps(event_data)
            # No widget but tool may have returned user_message (e.g. informational)
            if user_message and isinstance(user_message, str) and user_message.strip():
                inject_synthetic_text_for_tool_message(
                    event_data, user_message.strip(), parts
                )
                return json.dumps(event_data)

        # Check for text content that contains a JSON widget definition
        text = part.get("text", "")
        if text and any(wt in text for wt in RENDERABLE_WIDGET_TYPES):
            # Try to extract JSON from the text
            try:
                # Look for JSON objects in the text
                json_match = re.search(
                    r'\{[^{}]*"type"\s*:\s*"[^"]+"\s*,[^{}]*"data"\s*:\s*\{.*?\}[^{}]*\}',
                    text,
                    re.DOTALL,
                )
                if json_match:
                    candidate = json.loads(json_match.group())
                    if candidate.get("type") in RENDERABLE_WIDGET_TYPES and isinstance(
                        candidate.get("data"), dict
                    ):
                        event_data["widget"] = candidate
                        logger.info(
                            f"[SSE] Extracted widget from text content: type={candidate['type']}"
                        )
                        inject_synthetic_text_for_widget(event_data, candidate, parts)
                        return json.dumps(event_data)
            except (json.JSONDecodeError, AttributeError):
                pass

            # Also try parsing the entire text as JSON
            try:
                candidate = json.loads(text)
                if (
                    isinstance(candidate, dict)
                    and candidate.get("type") in RENDERABLE_WIDGET_TYPES
                ):
                    if isinstance(candidate.get("data"), dict):
                        event_data["widget"] = candidate
                        logger.info(
                            f"[SSE] Extracted widget from full text JSON: type={candidate['type']}"
                        )
                        inject_synthetic_text_for_widget(event_data, candidate, parts)
                        return json.dumps(event_data)
            except (json.JSONDecodeError, TypeError):
                pass

    return event_json


def _summarize_args(args: Any, max_len: int = 200) -> str:
    """Summarize function_call args into a short human-readable string.

    Produces key: value pairs for dicts, or a truncated JSON string for other types.
    Always truncated to *max_len* characters.

    Args:
        args: The function call arguments (typically a dict).
        max_len: Maximum character length for the summary.

    Returns:
        A concise string representation of the arguments.
    """
    if not args:
        return ""
    if isinstance(args, dict):
        # Show key: value pairs, quoting string values
        pairs: list[str] = []
        for key, val in args.items():
            if isinstance(val, str):
                fragment = f'{key}: "{val}"'
            elif isinstance(val, (dict, list)):
                fragment = f"{key}: ({type(val).__name__})"
            else:
                fragment = f"{key}: {val}"
            pairs.append(fragment)
            # Stop early if already long enough
            if sum(len(p) for p in pairs) > max_len:
                break
        summary = ", ".join(pairs)
    else:
        summary = str(args)
    if len(summary) > max_len:
        summary = summary[: max_len - 3] + "..."
    return summary


def _summarize_response(response: Any, max_len: int = 200) -> str:
    """Summarize a function_response result into a short status string.

    Detects success/failure flags and extracts a brief description.

    Args:
        response: The function response data (typically a dict).
        max_len: Maximum character length for the summary.

    Returns:
        A concise string describing the tool result.
    """
    if not response:
        return "No response"
    if not isinstance(response, dict):
        text = str(response)
        return text[:max_len] if len(text) > max_len else text

    # Detect explicit success/failure
    success = response.get("success")
    error = response.get("error")
    if success is False:
        msg = error or response.get("user_message") or "Failed"
        prefix = "Failed"
    elif error:
        msg = str(error)
        prefix = "Error"
    else:
        msg = (
            response.get("user_message")
            or response.get("message")
            or response.get("result")
            or ""
        )
        prefix = "OK"

    if isinstance(msg, (dict, list)):
        msg = f"({type(msg).__name__})"
    msg = str(msg).strip()
    if msg:
        summary = f"{prefix}: {msg}"
    else:
        summary = prefix
    if len(summary) > max_len:
        summary = summary[: max_len - 3] + "..."
    return summary


def extract_traces_from_event(event_json: str) -> str:
    """Post-process an SSE event to inject reasoning trace custom_events.

    Scans ADK event content.parts for:
    - function_call parts  -> injects custom_event {type: "tool_call", name, input}
    - function_response parts -> injects custom_event {type: "tool_result", name, output}
    - author changes (delegation) -> injects status message

    The frontend already handles these fields in its SSE message handler
    (useAgentChat.ts) and renders them via ThoughtProcess.tsx.

    Args:
        event_json: The JSON string of the serialized ADK event.

    Returns:
        Modified JSON string with trace fields injected, or original if no trace found.
    """
    try:
        event_data = json.loads(event_json)
    except (json.JSONDecodeError, TypeError):
        return event_json

    # Skip events that already carry a custom_event (avoid duplication)
    if event_data.get("custom_event"):
        return event_json

    modified = False

    # --- Detect author change (agent delegation) ---
    author = event_data.get("author")
    if author and author not in ("user", "system"):
        # Inject a status message so the frontend shows "Delegating to <agent>"
        # Only inject when there is no existing status field
        if not event_data.get("status"):
            event_data["status"] = f"Delegating to {author}"
            modified = True

    # --- Scan content.parts for function_call / function_response ---
    content = event_data.get("content")
    if not content or not isinstance(content, dict):
        return json.dumps(event_data) if modified else event_json

    parts = content.get("parts") or []

    for part in parts:
        if not isinstance(part, dict):
            continue

        # --- function_call (tool invocation) ---
        func_call = part.get("function_call") or part.get("functionCall")
        if func_call:
            tool_name = func_call.get("name") or "unknown_tool"
            args = func_call.get("args") or func_call.get("arguments") or {}
            summary = _summarize_args(args)
            event_data["custom_event"] = {
                "type": "tool_call",
                "name": tool_name,
                "input": summary,
            }
            logger.debug("[SSE] Trace: tool_call %s — %s", tool_name, summary[:80])
            return json.dumps(event_data)

        # --- function_response (tool result) ---
        func_response = part.get("function_response") or part.get("functionResponse")
        if func_response:
            tool_name = func_response.get("name") or "unknown_tool"
            response_data = (
                func_response.get("response")
                or func_response.get("response_data")
                or {}
            )
            summary = _summarize_response(response_data)
            event_data["custom_event"] = {
                "type": "tool_result",
                "name": tool_name,
                "output": summary,
            }
            logger.debug("[SSE] Trace: tool_result %s — %s", tool_name, summary[:80])
            return json.dumps(event_data)

    return json.dumps(event_data) if modified else event_json


# Allowlist of event types that may pass through serialize_progress_event.
# Anything outside this set is coerced back to "director_progress" for safety
# (the queue is the single channel for live SSE progress updates).
_PROGRESS_EVENT_ALLOWLIST = {
    "director_progress",
    "tool_call_start",
    "tool_call_end",
}


def serialize_progress_event(event: dict) -> str:
    """Serialize a progress queue item as an SSE data payload.

    Supports both director-pipeline events (legacy shape with `stage`/`payload`)
    and tool-call boundary events (`tool_call_start` / `tool_call_end`) emitted
    from ADK before/after tool callbacks.

    The event's `event_type` (or legacy `type`) selects the serialization path:
      - "director_progress" → {event_type, stage, payload, timestamp}
      - "tool_call_start"   → {event_type, tool_name, ts}
      - "tool_call_end"     → {event_type, tool_name, duration_ms, status, ts}

    Unknown event types fall back to "director_progress" to preserve legacy
    behaviour for any callers still pushing untagged dicts onto the queue.

    Args:
        event: Dictionary representing a single progress event.

    Returns:
        JSON string for direct emission inside an `data: …\\n\\n` SSE frame.
    """
    raw_type = event.get("event_type") or event.get("type") or "director_progress"
    event_type = raw_type if raw_type in _PROGRESS_EVENT_ALLOWLIST else "director_progress"

    if event_type == "tool_call_start":
        payload = {
            "event_type": "tool_call_start",
            "tool_name": event.get("tool_name", "unknown_tool"),
            "ts": event.get("ts") or event.get("timestamp"),
        }
        return json.dumps(payload)

    if event_type == "tool_call_end":
        payload = {
            "event_type": "tool_call_end",
            "tool_name": event.get("tool_name", "unknown_tool"),
            "duration_ms": event.get("duration_ms"),
            "status": event.get("status", "ok"),
            "ts": event.get("ts") or event.get("timestamp"),
        }
        return json.dumps(payload)

    # Default: director_progress (legacy shape).
    payload = {
        "event_type": "director_progress",
        "stage": event.get("stage"),
        "payload": event.get("payload", {}),
        "timestamp": event.get("timestamp"),
    }
    return json.dumps(payload)


# Backward compatibility aliases - these are also exported from fast_api_app.py
# but having them here allows for cleaner imports in other modules
_extract_widget_from_event = extract_widget_from_event
_extract_traces_from_event = extract_traces_from_event
_is_model_unavailable_error = is_model_unavailable_error
_inject_synthetic_text_for_widget = inject_synthetic_text_for_widget
_inject_synthetic_text_for_tool_message = inject_synthetic_text_for_tool_message
_serialize_progress_event = serialize_progress_event
