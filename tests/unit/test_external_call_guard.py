from app.mcp.security.external_call_guard import (
    protect_text_payload,
    protect_url_payload,
    summarize_payload_for_audit,
)


def test_protect_text_payload_redacts_pii_for_outbound_calls():
    result = protect_text_payload("Contact jane@example.com or call 555-123-4567", field_name="query")

    assert result.outbound_value == result.audit_value
    assert "jane@example.com" not in result.outbound_value
    assert "555-123-4567" not in result.outbound_value
    assert result.metadata["pii_detected"] is True
    assert sorted(result.metadata["pii_types"]) == ["email", "phone_us"]


def test_protect_url_payload_redacts_sensitive_query_values():
    result = protect_url_payload("https://example.com/profile?email=jane@example.com&token=abc123&view=full")

    assert result.outbound_value.startswith("https://example.com/profile?")
    assert "jane@example.com" not in result.outbound_value
    assert "abc123" not in result.outbound_value
    assert "view=full" in result.outbound_value
    assert result.metadata["pii_detected"] is True
    assert "token" in result.metadata["redacted_query_keys"]


def test_summarize_payload_for_audit_finds_nested_pii_without_mutating_payload():
    payload = {
        "name": "Jane Doe",
        "contact": {
            "email": "jane@example.com",
            "phone": "555-123-4567",
        },
        "notes": ["Reach out tomorrow"],
    }

    summary = summarize_payload_for_audit(payload, field_name="submission")

    assert summary["pii_detected"] is True
    assert summary["redaction_count"] >= 2
    assert "contact.email" in summary["fields_with_pii"]
    assert "contact.phone" in summary["fields_with_pii"]
    assert "jane@example.com" not in summary["audit_preview"]
