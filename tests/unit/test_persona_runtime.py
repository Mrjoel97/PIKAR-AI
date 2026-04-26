from types import SimpleNamespace

import pytest

from app.personas.runtime import (
    filter_initiative_templates_for_persona,
    filter_workflow_templates_for_persona,
    resolve_request_persona,
)


def test_resolve_request_persona_prefers_explicit_query_over_header() -> None:
    request = SimpleNamespace(headers={"x-pikar-persona": "sme"}, cookies={})

    assert resolve_request_persona(request, explicit_persona="enterprise") == "enterprise"



def test_resolve_request_persona_uses_cookie_or_header() -> None:
    cookie_request = SimpleNamespace(headers={}, cookies={"x-pikar-persona": "startup"})
    header_request = SimpleNamespace(headers={"x-pikar-persona": "SME"}, cookies={})

    assert resolve_request_persona(cookie_request) == "startup"
    assert resolve_request_persona(header_request) == "sme"



def test_filter_workflow_templates_keeps_generic_and_prioritizes_exact_match() -> None:
    templates = [
        {"name": "Generic Ops", "personas_allowed": None},
        {"name": "Startup Growth Sprint", "personas_allowed": ["startup"]},
        {"name": "Enterprise Controls", "personas_allowed": ["enterprise"]},
    ]

    filtered = filter_workflow_templates_for_persona(templates, "startup")

    assert [template["name"] for template in filtered] == [
        "Startup Growth Sprint",
        "Generic Ops",
    ]



def test_filter_initiative_templates_keeps_generic_and_prioritizes_exact_match() -> None:
    templates = [
        {"title": "Generic Weekly Operating System", "persona": None},
        {"title": "SME Reporting Structure", "persona": "sme"},
        {"title": "Startup Launch Plan", "persona": "startup"},
    ]

    filtered = filter_initiative_templates_for_persona(templates, "sme")

    assert [template["title"] for template in filtered] == [
        "SME Reporting Structure",
        "Generic Weekly Operating System",
    ]


def test_persona_content_override_returns_all_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_ALL_PERSONA_CONTENT_FOR_TESTING", "true")

    workflow_templates = [
        {"name": "Startup Growth Sprint", "personas_allowed": ["startup"]},
        {"name": "Enterprise Controls", "personas_allowed": ["enterprise"]},
    ]
    initiative_templates = [
        {"title": "Startup Launch Plan", "persona": "startup"},
        {"title": "SME Reporting Structure", "persona": "sme"},
    ]

    assert {
        template["name"]
        for template in filter_workflow_templates_for_persona(
            workflow_templates, "startup"
        )
    } == {"Startup Growth Sprint", "Enterprise Controls"}
    assert {
        template["title"]
        for template in filter_initiative_templates_for_persona(
            initiative_templates, "startup"
        )
    } == {"Startup Launch Plan", "SME Reporting Structure"}
