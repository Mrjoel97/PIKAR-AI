"""Tests for SSE utility functions (app/sse_utils.py).

Covers widget extraction from ADK events, model-unavailability detection,
synthetic text injection, trace extraction, and progress event serialization.
"""

import json
import pytest

from app.sse_utils import (
    extract_widget_from_event,
    is_model_unavailable_error,
    inject_synthetic_text_for_widget,
    inject_synthetic_text_for_tool_message,
    extract_traces_from_event,
    serialize_progress_event,
    RENDERABLE_WIDGET_TYPES,
)


# =============================================================================
# extract_widget_from_event
# =============================================================================

class TestExtractWidgetFromEvent:
    """Tests for extracting widget definitions from SSE events."""

    def test_extracts_widget_from_function_response(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "response": {
                            "type": "revenue_chart",
                            "title": "Q1 Revenue",
                            "data": {"labels": [], "values": []},
                        }
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert "widget" in result
        assert result["widget"]["type"] == "revenue_chart"
        assert result["widget"]["title"] == "Q1 Revenue"

    def test_extracts_widget_from_camel_case_function_response(self):
        event = {
            "content": {
                "parts": [{
                    "functionResponse": {
                        "response": {
                            "type": "initiative_dashboard",
                            "title": "Dashboard",
                            "data": {"initiatives": []},
                        }
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert result["widget"]["type"] == "initiative_dashboard"

    def test_passes_through_non_widget_events(self):
        event = {"content": {"parts": [{"text": "Hello, world!"}]}}
        raw = json.dumps(event)
        result = extract_widget_from_event(raw)
        parsed = json.loads(result)
        assert "widget" not in parsed

    def test_handles_invalid_json(self):
        result = extract_widget_from_event("not json at all")
        assert result == "not json at all"

    def test_handles_empty_string(self):
        result = extract_widget_from_event("")
        assert result == ""

    def test_skips_failed_tool_results(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "response": {
                            "success": False,
                            "error": "Something failed",
                        }
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert "widget" not in result

    def test_injects_error_message_for_failed_tool_with_user_message(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "response": {
                            "success": False,
                            "user_message": "Could not generate chart",
                        }
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert "widget" not in result
        # The error text should be injected into parts
        parts = result["content"]["parts"]
        text_parts = [p for p in parts if isinstance(p, dict) and p.get("text")]
        assert any("Could not generate chart" in p["text"] for p in text_parts)

    def test_passes_through_event_with_existing_widget(self):
        event = {
            "widget": {"type": "table", "data": {}},
            "content": {"parts": []},
        }
        raw = json.dumps(event)
        result = extract_widget_from_event(raw)
        assert result == raw

    def test_handles_event_without_content(self):
        event = {"author": "agent"}
        raw = json.dumps(event)
        result = extract_widget_from_event(raw)
        assert result == raw

    def test_handles_top_level_error_in_function_response(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "error": "Tool crashed unexpectedly",
                        "response": {},
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert "widget" not in result
        parts = result["content"]["parts"]
        text_parts = [p for p in parts if isinstance(p, dict) and p.get("text")]
        assert any("Tool Execution Error" in p["text"] for p in text_parts)

    def test_extracts_widget_from_nested_result_key(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "response": {
                            "result": {
                                "type": "kanban_board",
                                "title": "Board",
                                "data": {"columns": [], "cards": []},
                            }
                        }
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert result["widget"]["type"] == "kanban_board"

    def test_extracts_widget_from_text_json(self):
        widget_def = {
            "type": "form",
            "title": "Contact Form",
            "data": {"fields": []},
        }
        event = {
            "content": {
                "parts": [{"text": json.dumps(widget_def)}]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert result["widget"]["type"] == "form"

    def test_ignores_text_with_non_renderable_widget_type(self):
        event = {
            "content": {
                "parts": [{"text": '{"type": "custom_nonsense", "data": {}}'}]
            }
        }
        raw = json.dumps(event)
        result = extract_widget_from_event(raw)
        parsed = json.loads(result)
        assert "widget" not in parsed

    def test_injects_user_message_when_no_widget_but_message_present(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "response": {
                            "user_message": "Task completed successfully",
                        }
                    }
                }]
            }
        }
        result = json.loads(extract_widget_from_event(json.dumps(event)))
        assert "widget" not in result
        parts = result["content"]["parts"]
        text_parts = [p for p in parts if isinstance(p, dict) and p.get("text")]
        assert any("Task completed successfully" in p["text"] for p in text_parts)


# =============================================================================
# is_model_unavailable_error
# =============================================================================

class TestIsModelUnavailableError:
    """Tests for model unavailability detection."""

    def test_detects_404_in_message(self):
        assert is_model_unavailable_error(Exception("404 Model Not Found")) is True

    def test_detects_429_in_message(self):
        assert is_model_unavailable_error(Exception("429 Rate limit exceeded")) is True

    def test_detects_resource_exhausted(self):
        assert is_model_unavailable_error(Exception("RESOURCE_EXHAUSTED: quota exceeded")) is True

    def test_detects_not_found(self):
        assert is_model_unavailable_error(Exception("NOT_FOUND: model does not exist")) is True

    def test_detects_model_unavailable(self):
        assert is_model_unavailable_error(Exception("MODEL is UNAVAILABLE")) is True

    def test_detects_model_not_found(self):
        assert is_model_unavailable_error(Exception("Model Not Found in region")) is True

    def test_detects_model_invalid(self):
        assert is_model_unavailable_error(Exception("Model INVALID for this request")) is True

    def test_ignores_normal_errors(self):
        assert is_model_unavailable_error(Exception("Some random error")) is False

    def test_ignores_empty_message(self):
        assert is_model_unavailable_error(Exception("")) is False

    def test_case_insensitive_matching(self):
        # The implementation uppercases the message
        assert is_model_unavailable_error(Exception("resource_exhausted")) is True


# =============================================================================
# inject_synthetic_text_for_widget
# =============================================================================

class TestInjectSyntheticTextForWidget:
    """Tests for synthetic text injection for widget events."""

    def test_does_nothing_if_text_part_already_exists(self):
        event_data = {"content": {"parts": [{"text": "Already here"}]}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "revenue_chart", "title": "Revenue"}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        # parts list should be unchanged (still only 1 text part)
        assert len(event_data["content"]["parts"]) == 1
        assert event_data["content"]["parts"][0]["text"] == "Already here"

    def test_injects_user_message_when_present(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "table", "user_message": "Here is your data table."}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert any("Here is your data table." in t for t in text_parts)

    def test_injects_title_as_fallback(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "table", "title": "Sales Data"}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert any("Sales Data" in t for t in text_parts)

    def test_injects_video_default_text(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "video", "data": {}}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert any("video" in t.lower() for t in text_parts)

    def test_injects_image_default_text(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "image", "data": {}}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert any("image" in t.lower() for t in text_parts)

    def test_injects_generic_fallback(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "kanban_board", "data": {}}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert any("created for you" in t.lower() for t in text_parts)

    def test_handles_non_dict_content(self):
        event_data = {"content": "not a dict"}
        inject_synthetic_text_for_widget(event_data, {"type": "table"}, [])
        # Should not crash, content stays as-is
        assert event_data["content"] == "not a dict"

    def test_injects_caption_from_data(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        widget_def = {"type": "image", "data": {"caption": "A beautiful chart"}}
        inject_synthetic_text_for_widget(event_data, widget_def, parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert any("A beautiful chart" in t for t in text_parts)


# =============================================================================
# inject_synthetic_text_for_tool_message
# =============================================================================

class TestInjectSyntheticTextForToolMessage:
    """Tests for synthetic text injection for tool error/info messages."""

    def test_injects_text_when_no_existing_text_part(self):
        event_data = {"content": {"parts": []}}
        parts = event_data["content"]["parts"]
        inject_synthetic_text_for_tool_message(event_data, "Operation complete", parts)
        text_parts = [p["text"] for p in event_data["content"]["parts"] if p.get("text")]
        assert "Operation complete" in text_parts

    def test_does_nothing_if_text_already_exists(self):
        event_data = {"content": {"parts": [{"text": "Existing text"}]}}
        parts = event_data["content"]["parts"]
        inject_synthetic_text_for_tool_message(event_data, "Should not appear", parts)
        assert len(event_data["content"]["parts"]) == 1


# =============================================================================
# extract_traces_from_event
# =============================================================================

class TestExtractTracesFromEvent:
    """Tests for reasoning trace extraction from SSE events."""

    def test_extracts_tool_call_trace(self):
        event = {
            "content": {
                "parts": [{
                    "function_call": {
                        "name": "search_knowledge",
                        "args": {"query": "revenue Q1"},
                    }
                }]
            }
        }
        result = json.loads(extract_traces_from_event(json.dumps(event)))
        assert result["custom_event"]["type"] == "tool_call"
        assert result["custom_event"]["name"] == "search_knowledge"

    def test_extracts_tool_result_trace(self):
        event = {
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "search_knowledge",
                        "response": {"success": True, "message": "Found 3 results"},
                    }
                }]
            }
        }
        result = json.loads(extract_traces_from_event(json.dumps(event)))
        assert result["custom_event"]["type"] == "tool_result"
        assert result["custom_event"]["name"] == "search_knowledge"

    def test_injects_delegation_status(self):
        event = {"author": "financial_agent", "content": {"parts": []}}
        result = json.loads(extract_traces_from_event(json.dumps(event)))
        assert "financial_agent" in result["status"]

    def test_does_not_inject_delegation_for_user(self):
        event = {"author": "user", "content": {"parts": [{"text": "Hi"}]}}
        raw = json.dumps(event)
        result = json.loads(extract_traces_from_event(raw))
        assert "status" not in result

    def test_skips_events_with_existing_custom_event(self):
        event = {
            "custom_event": {"type": "existing"},
            "content": {"parts": [{"function_call": {"name": "test"}}]},
        }
        raw = json.dumps(event)
        result = extract_traces_from_event(raw)
        assert result == raw

    def test_handles_invalid_json(self):
        result = extract_traces_from_event("not valid json")
        assert result == "not valid json"

    def test_handles_camel_case_function_call(self):
        event = {
            "content": {
                "parts": [{
                    "functionCall": {
                        "name": "create_task",
                        "arguments": {"title": "Test task"},
                    }
                }]
            }
        }
        result = json.loads(extract_traces_from_event(json.dumps(event)))
        assert result["custom_event"]["type"] == "tool_call"
        assert result["custom_event"]["name"] == "create_task"


# =============================================================================
# serialize_progress_event
# =============================================================================

class TestSerializeProgressEvent:
    """Tests for director progress event serialization."""

    def test_serializes_progress_event(self):
        event = {
            "stage": "rendering",
            "payload": {"frame": 42, "total": 120},
            "timestamp": "2026-03-20T10:00:00Z",
        }
        result = json.loads(serialize_progress_event(event))
        assert result["event_type"] == "director_progress"
        assert result["stage"] == "rendering"
        assert result["payload"]["frame"] == 42
        assert result["timestamp"] == "2026-03-20T10:00:00Z"

    def test_defaults_payload_to_empty_dict(self):
        event = {"stage": "done"}
        result = json.loads(serialize_progress_event(event))
        assert result["payload"] == {}

    def test_handles_missing_fields(self):
        result = json.loads(serialize_progress_event({}))
        assert result["stage"] is None
        assert result["timestamp"] is None


# =============================================================================
# RENDERABLE_WIDGET_TYPES constant
# =============================================================================

class TestRenderableWidgetTypes:
    """Tests for the renderable widget types set."""

    def test_contains_core_types(self):
        expected = {
            "initiative_dashboard", "revenue_chart", "product_launch",
            "kanban_board", "workflow_builder", "morning_briefing",
            "boardroom", "form", "table", "calendar", "workflow",
            "image", "video", "video_spec",
        }
        assert expected.issubset(RENDERABLE_WIDGET_TYPES)

    def test_is_a_set(self):
        assert isinstance(RENDERABLE_WIDGET_TYPES, set)
