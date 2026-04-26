"""Tests for _extract_widget_from_event in the SSE endpoint.

Validates that widget definitions are correctly extracted from ADK event
payloads and injected as top-level 'widget' fields for the frontend.
"""

import json


# We import the function directly since it's a pure function
# that doesn't depend on FastAPI app state
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import from the extracted module
from app.sse_utils import extract_widget_from_event, RENDERABLE_WIDGET_TYPES

# Backward compatibility alias
_extract_widget_from_event = extract_widget_from_event


class TestExtractWidgetFromEvent:
    """Tests for the SSE widget extraction middleware."""

    def test_passthrough_non_widget_event(self):
        """Normal text events should pass through unchanged."""
        event = json.dumps({
            "author": "ExecutiveAgent",
            "content": {
                "parts": [{"text": "Hello! How can I help you today?"}]
            }
        })
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" not in result
        assert result["content"]["parts"][0]["text"] == "Hello! How can I help you today?"

    def test_extract_widget_from_function_response(self):
        """Widget dicts in function_response should be extracted."""
        event = json.dumps({
            "author": "ExecutiveAgent",
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "create_revenue_chart_widget",
                        "response": {
                            "type": "revenue_chart",
                            "title": "Revenue Overview",
                            "data": {
                                "periods": ["Jan", "Feb"],
                                "values": [1000, 1500],
                                "currency": "USD"
                            },
                            "dismissible": True,
                            "expandable": True
                        }
                    }
                }]
            }
        })
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" in result
        assert result["widget"]["type"] == "revenue_chart"
        assert result["widget"]["title"] == "Revenue Overview"
        assert result["widget"]["data"]["periods"] == ["Jan", "Feb"]

    def test_extract_widget_from_nested_result(self):
        """Widget dicts nested in function_response.response.result should be extracted."""
        event = json.dumps({
            "author": "ExecutiveAgent",
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "create_form_widget",
                        "response": {
                            "result": {
                                "type": "form",
                                "title": "Feedback Form",
                                "data": {
                                    "fields": [{"name": "email", "label": "Email", "type": "email"}],
                                    "submitLabel": "Submit"
                                },
                                "dismissible": True
                            }
                        }
                    }
                }]
            }
        })
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" in result
        assert result["widget"]["type"] == "form"

    def test_extract_widget_from_text_json(self):
        """Widget JSON embedded in text content should be extracted."""
        widget_json = json.dumps({
            "type": "kanban_board",
            "title": "Project Board",
            "data": {
                "columns": [{"id": "todo", "title": "To Do"}],
                "cards": []
            },
            "dismissible": True
        })
        event = json.dumps({
            "author": "ExecutiveAgent",
            "content": {
                "parts": [{"text": widget_json}]
            }
        })
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" in result
        assert result["widget"]["type"] == "kanban_board"

    def test_skip_already_has_widget(self):
        """Events that already have a widget field should be left unchanged."""
        existing_widget = {
            "type": "table",
            "title": "Data Table",
            "data": {"columns": [], "rows": []}
        }
        event = json.dumps({
            "author": "ExecutiveAgent",
            "widget": existing_widget,
            "content": {"parts": [{"text": "Here's your table"}]}
        })
        result = json.loads(_extract_widget_from_event(event))
        assert result["widget"] == existing_widget

    def test_no_content_event(self):
        """Events without content should pass through."""
        event = json.dumps({"status": "processing"})
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" not in result

    def test_invalid_json_passthrough(self):
        """Invalid JSON should be returned as-is."""
        bad_json = "not valid json"
        assert _extract_widget_from_event(bad_json) == bad_json

    def test_all_widget_types_recognized(self):
        """All widget types (including image, video, video_spec) should be in RENDERABLE_WIDGET_TYPES."""
        expected = {
            'initiative_dashboard', 'revenue_chart', 'product_launch',
            'kanban_board', 'workflow_builder', 'morning_briefing',
            'boardroom', 'suggested_workflows', 'form', 'table',
            'calendar', 'workflow', 'image', 'video', 'video_spec',
            'api_connections', 'department_activity', 'app_builder_launcher',
        }
        assert RENDERABLE_WIDGET_TYPES == expected

    def test_non_widget_function_response_ignored(self):
        """Function responses that aren't widgets should be ignored."""
        event = json.dumps({
            "author": "ExecutiveAgent",
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "get_revenue_stats",
                        "response": {
                            "revenue": 1000.0,
                            "currency": "USD"
                        }
                    }
                }]
            }
        })
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" not in result

    def test_multiple_parts_extracts_first_widget(self):
        """When multiple parts have widgets, extract from the first one found."""
        event = json.dumps({
            "author": "ExecutiveAgent",
            "content": {
                "parts": [
                    {"text": "Here's your data:"},
                    {
                        "function_response": {
                            "name": "create_table_widget",
                            "response": {
                                "type": "table",
                                "title": "Lead List",
                                "data": {
                                    "columns": [{"key": "name", "label": "Name"}],
                                    "rows": [{"name": "Alice"}]
                                },
                                "dismissible": True
                            }
                        }
                    }
                ]
            }
        })
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" in result
        assert result["widget"]["type"] == "table"

    def test_extract_all_widget_types(self):
        """Each widget type should be extractable from a function_response."""
        for widget_type in RENDERABLE_WIDGET_TYPES:
            event = json.dumps({
                "content": {
                    "parts": [{
                        "function_response": {
                            "name": f"create_{widget_type}_widget",
                            "response": {
                                "type": widget_type,
                                "title": f"Test {widget_type}",
                                "data": {"test": True}
                            }
                        }
                    }]
                }
            })
            result = json.loads(_extract_widget_from_event(event))
            assert "widget" in result, f"Failed to extract widget type: {widget_type}"
            assert result["widget"]["type"] == widget_type
