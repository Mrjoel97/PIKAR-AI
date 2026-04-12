# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for generate_sop_document tool.

Covers structured SOP output, formatted text sections, minimal input handling,
workflow suggestion, and document ID format.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_STEPS = [
    "Receive the customer complaint via email or phone",
    "Log the complaint in the ticketing system",
    "Escalate to the appropriate department within 1 hour",
    "Send acknowledgement to customer within 4 hours",
    "Resolve and close ticket within 48 hours",
]

_FULL_ROLES = ["Customer Support Rep", "Department Manager", "Customer Support Rep", "Customer Support Rep", "Resolution Team"]


# ---------------------------------------------------------------------------
# Test 1: generate_sop_document returns structured SOP with required keys
# ---------------------------------------------------------------------------


def test_generate_sop_document_returns_structured_sop():
    """Tool returns status=success with a structured SOP containing all required keys."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Customer Complaint Handling",
        process_description="Process for handling customer complaints to ensure timely resolution.",
        steps=_FULL_STEPS,
        roles=_FULL_ROLES,
        department="Customer Support",
    )

    assert result["status"] == "success"
    sop = result["sop"]
    assert "document_id" in sop
    assert "title" in sop
    assert "version" in sop
    assert "effective_date" in sop
    assert "department" in sop
    assert "purpose" in sop
    assert "scope" in sop
    assert "procedure" in sop
    assert "quality_checks" in sop
    assert "revision_history" in sop


# ---------------------------------------------------------------------------
# Test 2: SOP contains correct data values
# ---------------------------------------------------------------------------


def test_generate_sop_document_correct_data_values():
    """SOP fields contain the provided data."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Customer Complaint Handling",
        process_description="Process for handling customer complaints.",
        steps=_FULL_STEPS,
        roles=_FULL_ROLES,
        department="Customer Support",
    )

    sop = result["sop"]
    assert sop["version"] == "1.0"
    assert sop["department"] == "Customer Support"
    assert sop["purpose"] == "Process for handling customer complaints."
    assert "Customer Complaint Handling" in sop["title"]
    assert len(sop["procedure"]) == len(_FULL_STEPS)
    # Each procedure step has step_number and action
    for i, step in enumerate(sop["procedure"]):
        assert step["step_number"] == i + 1
        assert step["action"] == _FULL_STEPS[i]
        assert "responsible" in step


# ---------------------------------------------------------------------------
# Test 3: SOP with minimal input (no roles, default department)
# ---------------------------------------------------------------------------


def test_generate_sop_document_minimal_input():
    """Tool handles minimal input (no roles, default department) gracefully."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Onboarding New Employees",
        process_description="Steps to onboard a new employee.",
        steps=["Create accounts", "Assign workspace", "Schedule orientation"],
    )

    assert result["status"] == "success"
    sop = result["sop"]
    # Default department applied
    assert sop["department"] == "Operations"
    # Roles default to 'All team members'
    assert sop["scope"]["applies_to"] == ["All team members"]
    # Responsible defaults to 'Assigned team member'
    for step in sop["procedure"]:
        assert step["responsible"] == "Assigned team member"


# ---------------------------------------------------------------------------
# Test 4: formatted_text contains all SOP sections
# ---------------------------------------------------------------------------


def test_generate_sop_document_formatted_text_contains_sections():
    """formatted_text output contains Purpose, Scope, Procedure, and Quality Checks sections."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Invoice Processing",
        process_description="Process to handle incoming invoices.",
        steps=["Receive invoice", "Verify details", "Approve payment", "File record"],
        roles=["Finance Clerk", "Finance Manager", "CFO", "Finance Clerk"],
    )

    text = result["formatted_text"]
    assert "Purpose" in text
    assert "Scope" in text
    assert "Procedure" in text
    assert "Quality Checks" in text
    assert "Revision History" in text
    assert "Invoice Processing" in text


# ---------------------------------------------------------------------------
# Test 5: suggestion key is present and contains workflow offer
# ---------------------------------------------------------------------------


def test_generate_sop_document_includes_workflow_suggestion():
    """Result includes a suggestion offering to create a workflow template."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Budget Approval",
        process_description="Steps for budget approval process.",
        steps=["Submit request", "Review by manager", "CFO approval", "Notify submitter"],
    )

    assert "suggestion" in result
    suggestion = result["suggestion"]
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0
    # Should mention workflow template creation
    assert "workflow" in suggestion.lower() or "template" in suggestion.lower()


# ---------------------------------------------------------------------------
# Test 6: document_id format
# ---------------------------------------------------------------------------


def test_generate_sop_document_id_format():
    """document_id follows SOP-DEP-TIMESTAMP format."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Server Deployment",
        process_description="Steps for deploying to production.",
        steps=["Create PR", "Run tests", "Merge", "Deploy"],
        department="Engineering",
    )

    doc_id = result["sop"]["document_id"]
    assert doc_id.startswith("SOP-ENG-")
    # After the prefix, there should be a timestamp
    parts = doc_id.split("-")
    assert len(parts) >= 3


# ---------------------------------------------------------------------------
# Test 7: quality_checks are present with standard entries
# ---------------------------------------------------------------------------


def test_generate_sop_document_quality_checks():
    """SOP includes at least one quality check."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Data Backup",
        process_description="Daily data backup procedure.",
        steps=["Initiate backup", "Verify completion", "Store offsite"],
    )

    quality_checks = result["sop"]["quality_checks"]
    assert isinstance(quality_checks, list)
    assert len(quality_checks) >= 1


# ---------------------------------------------------------------------------
# Test 8: revision_history initial entry
# ---------------------------------------------------------------------------


def test_generate_sop_document_revision_history():
    """SOP revision_history has an initial creation entry."""
    from app.agents.tools.ops_tools import generate_sop_document

    result = generate_sop_document(
        process_name="Vendor Onboarding",
        process_description="Process for onboarding new vendors.",
        steps=["Collect docs", "Legal review", "Sign contract", "Setup in system"],
    )

    history = result["sop"]["revision_history"]
    assert len(history) >= 1
    first = history[0]
    assert first["version"] == "1.0"
    assert "date" in first
    assert "author" in first
    assert "changes" in first
