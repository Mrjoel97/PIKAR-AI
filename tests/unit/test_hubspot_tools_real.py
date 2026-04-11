# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the real HubSpot tools added in Phase 62 Plan 04.

Covers:
- score_hubspot_lead: HubSpot-connected and local-only paths
- query_hubspot_crm: contacts and deals queries with filters
- sync_deal_notes: note push and local-only fallback paths
- Missing user_id error handling for all three tools
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

FAKE_USER_ID = "user-123"
FAKE_CONTACT_ID = "contact-abc"
FAKE_DEAL_ID = "deal-xyz"


def _mock_result(data: list | None = None) -> MagicMock:
    """Return a plain mock whose .data attribute holds *data*."""
    result = MagicMock()
    result.data = data or []
    return result


def _async_result(data: list | None = None) -> AsyncMock:
    """Return an AsyncMock that resolves to a result with .data set to *data*."""
    return AsyncMock(return_value=_mock_result(data))


# Backwards-compat alias used in side_effect lists
def _mock_execute_async(data: list | None = None) -> AsyncMock:
    """Return an awaitable mock whose .data is set to *data*."""
    return _async_result(data)


def _admin_mock() -> MagicMock:
    """Return a MagicMock that simulates AdminService with a chainable client."""
    admin = MagicMock()
    # Make the client's table/select/eq/or_/limit/insert/update chain return
    # something that won't raise; actual DB calls are intercepted by
    # ``_execute_async_query`` mock.
    admin.client.table.return_value = admin.client
    for method in ("select", "eq", "or_", "limit", "insert", "update", "order"):
        getattr(admin.client, method).return_value = admin.client
    return admin


# ---------------------------------------------------------------------------
# score_hubspot_lead
# ---------------------------------------------------------------------------


class TestScoreHubspotLead:
    """Tests for score_hubspot_lead tool."""

    @pytest.mark.asyncio
    async def test_score_lead_pushes_to_hubspot_when_connected(self):
        """Test 1: score_hubspot_lead updates contact properties in HubSpot."""
        contact_row = {
            "id": FAKE_CONTACT_ID,
            "name": "Alice Example",
            "email": "alice@example.com",
            "hubspot_contact_id": "hs-001",
            "lifecycle_stage": "lead",
            "metadata": {},
        }
        activity_row = {"id": "act-1"}

        admin = _admin_mock()

        with (
            patch(
                "app.agents.tools.hubspot_tools._get_user_id",
                return_value=FAKE_USER_ID,
            ),
            patch(
                "app.agents.tools.hubspot_tools.AdminService",
                return_value=admin,
            ),
            patch(
                "app.agents.tools.hubspot_tools._execute_async_query"
            ) as mock_query,
            patch(
                "app.agents.tools.hubspot_tools.HubSpotService"
            ) as MockSvc,
        ):
            # First call: find contact; Second call: log activity
            mock_query.side_effect = [
                _mock_execute_async([contact_row]),
                _mock_execute_async([activity_row]),
            ]
            svc_instance = MockSvc.return_value
            svc_instance.update_contact_score = AsyncMock(
                return_value={"hubspot_contact_id": "hs-001", "status": "updated"}
            )

            from app.agents.tools.hubspot_tools import score_hubspot_lead

            result = await score_hubspot_lead(
                contact_name_or_email="alice@example.com",
                score=82,
                framework="BANT",
                qualification_notes="Strong budget and authority confirmed",
            )

        assert result["success"] is True
        assert result["score"] == 82
        assert result["synced_to_hubspot"] is True
        svc_instance.update_contact_score.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_score_lead_falls_back_to_local_when_not_connected(self):
        """Test 2: score_hubspot_lead falls back to local-only when HubSpot not connected."""
        contact_row = {
            "id": FAKE_CONTACT_ID,
            "name": "Bob Lead",
            "email": "bob@example.com",
            "hubspot_contact_id": None,
            "lifecycle_stage": "lead",
            "metadata": {},
        }
        activity_row = {"id": "act-2"}

        admin = _admin_mock()

        with (
            patch(
                "app.agents.tools.hubspot_tools._get_user_id",
                return_value=FAKE_USER_ID,
            ),
            patch(
                "app.agents.tools.hubspot_tools.AdminService",
                return_value=admin,
            ),
            patch(
                "app.agents.tools.hubspot_tools._execute_async_query"
            ) as mock_query,
            patch(
                "app.agents.tools.hubspot_tools.HubSpotService"
            ) as MockSvc,
        ):
            mock_query.side_effect = [
                _mock_execute_async([contact_row]),
                _mock_execute_async([activity_row]),
            ]
            svc_instance = MockSvc.return_value
            svc_instance.update_contact_score = AsyncMock(
                side_effect=ValueError("No HubSpot connection found")
            )

            from app.agents.tools.hubspot_tools import score_hubspot_lead

            result = await score_hubspot_lead(
                contact_name_or_email="bob@example.com",
                score=60,
            )

        assert result["success"] is True
        assert result["score"] == 60
        # No hubspot_contact_id on the contact, so no sync attempted
        assert result["synced_to_hubspot"] is False

    @pytest.mark.asyncio
    async def test_score_lead_returns_error_without_user_id(self):
        """Test 7a: score_hubspot_lead returns error dict when no user_id in context."""
        with patch(
            "app.agents.tools.hubspot_tools._get_user_id",
            return_value=None,
        ):
            from app.agents.tools.hubspot_tools import score_hubspot_lead

            result = await score_hubspot_lead(
                contact_name_or_email="anyone@example.com",
                score=50,
            )

        assert "error" in result
        assert result["error"] == "Authentication required"


# ---------------------------------------------------------------------------
# query_hubspot_crm
# ---------------------------------------------------------------------------


class TestQueryHubspotCrm:
    """Tests for query_hubspot_crm tool."""

    @pytest.mark.asyncio
    async def test_query_crm_returns_contacts_from_local_table(self):
        """Test 3: query_hubspot_crm returns real contacts from local CRM tables."""
        contacts = [
            {
                "id": "c1",
                "name": "Carol Smith",
                "email": "carol@corp.com",
                "lifecycle_stage": "qualified",
                "source": "inbound",
                "created_at": "2025-01-15T00:00:00Z",
            },
            {
                "id": "c2",
                "name": "Dave Jones",
                "email": "dave@corp.com",
                "lifecycle_stage": "qualified",
                "source": "inbound",
                "created_at": "2025-02-10T00:00:00Z",
            },
        ]

        admin = _admin_mock()

        with (
            patch(
                "app.agents.tools.hubspot_tools._get_user_id",
                return_value=FAKE_USER_ID,
            ),
            patch(
                "app.agents.tools.hubspot_tools.AdminService",
                return_value=admin,
            ),
            patch(
                "app.agents.tools.hubspot_tools._execute_async_query",
                new_callable=AsyncMock,
                return_value=_mock_result(contacts),
            ),
        ):
            from app.agents.tools.hubspot_tools import query_hubspot_crm

            result = await query_hubspot_crm(query_type="contacts")

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert "aggregations" in result

    @pytest.mark.asyncio
    async def test_query_crm_filters_by_lifecycle_stage_and_source(self):
        """Test 4: query_hubspot_crm supports filtering by lifecycle_stage and source."""
        filtered_contacts = [
            {
                "id": "c3",
                "name": "Eve Lead",
                "email": "eve@startup.io",
                "lifecycle_stage": "customer",
                "source": "referral",
                "created_at": "2025-03-01T00:00:00Z",
            }
        ]

        admin = _admin_mock()

        with (
            patch(
                "app.agents.tools.hubspot_tools._get_user_id",
                return_value=FAKE_USER_ID,
            ),
            patch(
                "app.agents.tools.hubspot_tools.AdminService",
                return_value=admin,
            ),
            patch(
                "app.agents.tools.hubspot_tools._execute_async_query",
                new_callable=AsyncMock,
                return_value=_mock_result(filtered_contacts),
            ),
        ):
            from app.agents.tools.hubspot_tools import query_hubspot_crm

            result = await query_hubspot_crm(
                query_type="contacts",
                lifecycle_stage="customer",
                source="referral",
                limit=10,
            )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"][0]["lifecycle_stage"] == "customer"

    @pytest.mark.asyncio
    async def test_query_crm_returns_error_without_user_id(self):
        """Test 7b: query_hubspot_crm returns error dict when no user_id in context."""
        with patch(
            "app.agents.tools.hubspot_tools._get_user_id",
            return_value=None,
        ):
            from app.agents.tools.hubspot_tools import query_hubspot_crm

            result = await query_hubspot_crm()

        assert "error" in result
        assert result["error"] == "Authentication required"


# ---------------------------------------------------------------------------
# sync_deal_notes
# ---------------------------------------------------------------------------


class TestSyncDealNotes:
    """Tests for sync_deal_notes tool."""

    @pytest.mark.asyncio
    async def test_sync_deal_notes_pushes_to_hubspot(self):
        """Test 5: sync_deal_notes pushes notes and stage change to HubSpot deal properties."""
        deal_row = {
            "id": FAKE_DEAL_ID,
            "deal_name": "Acme Enterprise",
            "stage": "proposal",
            "hubspot_deal_id": "hs-deal-001",
            "user_id": FAKE_USER_ID,
            "properties": {},
        }

        admin = _admin_mock()

        with (
            patch(
                "app.agents.tools.hubspot_tools._get_user_id",
                return_value=FAKE_USER_ID,
            ),
            patch(
                "app.agents.tools.hubspot_tools.AdminService",
                return_value=admin,
            ),
            patch(
                "app.agents.tools.hubspot_tools._execute_async_query"
            ) as mock_query,
            patch(
                "app.agents.tools.hubspot_tools.HubSpotService"
            ) as MockSvc,
        ):
            # First call: find deal; Second call: update local props
            mock_query.side_effect = [
                _mock_execute_async([deal_row]),
                _mock_execute_async([deal_row]),
            ]
            svc_instance = MockSvc.return_value
            svc_instance.add_deal_note = AsyncMock(
                return_value={
                    "note_id": "note-001",
                    "status": "created",
                    "stage_changed": True,
                }
            )

            from app.agents.tools.hubspot_tools import sync_deal_notes

            result = await sync_deal_notes(
                deal_name_or_id="Acme Enterprise",
                notes="Called CEO, confirmed budget of $200K. Moving to negotiation.",
                next_steps=["Send contract by Friday", "Schedule legal review"],
                stage_change="negotiation",
            )

        assert result["success"] is True
        assert result["synced_to_hubspot"] is True
        assert result["stage_changed"] is True
        svc_instance.add_deal_note.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_deal_notes_updates_local_when_not_connected(self):
        """Test 6: sync_deal_notes updates local hubspot_deals table when HubSpot not connected."""
        deal_row = {
            "id": FAKE_DEAL_ID,
            "deal_name": "Local Only Deal",
            "stage": "discovery",
            "hubspot_deal_id": None,
            "user_id": FAKE_USER_ID,
            "properties": {},
        }

        admin = _admin_mock()

        with (
            patch(
                "app.agents.tools.hubspot_tools._get_user_id",
                return_value=FAKE_USER_ID,
            ),
            patch(
                "app.agents.tools.hubspot_tools.AdminService",
                return_value=admin,
            ),
            patch(
                "app.agents.tools.hubspot_tools._execute_async_query"
            ) as mock_query,
            patch(
                "app.agents.tools.hubspot_tools.HubSpotService"
            ) as MockSvc,
        ):
            mock_query.side_effect = [
                _mock_execute_async([deal_row]),
                _mock_execute_async([deal_row]),
            ]
            svc_instance = MockSvc.return_value
            svc_instance.add_deal_note = AsyncMock(
                side_effect=ValueError("No HubSpot connection found")
            )

            from app.agents.tools.hubspot_tools import sync_deal_notes

            result = await sync_deal_notes(
                deal_name_or_id="Local Only Deal",
                notes="Had a great discovery call. Strong fit identified.",
                next_steps=["Prepare proposal"],
            )

        assert result["success"] is True
        # No hubspot_deal_id, so local-only
        assert result["synced_to_hubspot"] is False

    @pytest.mark.asyncio
    async def test_sync_deal_notes_returns_error_without_user_id(self):
        """Test 7c: sync_deal_notes returns error dict when no user_id in context."""
        with patch(
            "app.agents.tools.hubspot_tools._get_user_id",
            return_value=None,
        ):
            from app.agents.tools.hubspot_tools import sync_deal_notes

            result = await sync_deal_notes(
                deal_name_or_id="Some Deal",
                notes="Some notes",
            )

        assert "error" in result
        assert result["error"] == "Authentication required"


# ---------------------------------------------------------------------------
# HUBSPOT_TOOLS export length
# ---------------------------------------------------------------------------


class TestHubspotToolsExport:
    """Tests for the HUBSPOT_TOOLS export list."""

    def test_hubspot_tools_has_eight_entries(self):
        """Verify HUBSPOT_TOOLS contains all 8 tools (5 existing + 3 new)."""
        from app.agents.tools.hubspot_tools import HUBSPOT_TOOLS

        assert len(HUBSPOT_TOOLS) == 8, (
            f"Expected 8 HubSpot tools, found {len(HUBSPOT_TOOLS)}: "
            f"{[fn.__name__ for fn in HUBSPOT_TOOLS]}"
        )

    def test_new_tools_are_in_export(self):
        """Verify the three new tools are present in HUBSPOT_TOOLS."""
        from app.agents.tools.hubspot_tools import (
            HUBSPOT_TOOLS,
            query_hubspot_crm,
            score_hubspot_lead,
            sync_deal_notes,
        )

        tool_names = {fn.__name__ for fn in HUBSPOT_TOOLS}
        assert "score_hubspot_lead" in tool_names
        assert "query_hubspot_crm" in tool_names
        assert "sync_deal_notes" in tool_names
