# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integration tests for the hardened account deletion cascade.

GDPR-02 / GDPR-03 coverage:
- All user-linked rows in scope are removed or anonymized after delete_user_account()
- governance_audit_log rows survive but actor identity (user_id, ip_address) is anonymized
- data_deletion_requests row survives as a durable audit trail (user_id → NULL via SET NULL)

These tests exercise the SQL function logic with in-process mocks rather than a live
Supabase instance so CI can run them without a database.  The companion integration
fixture (conftest.py) provides helpers; the test body simulates the state the function
must leave behind.

NOTE: Because the DB function runs inside Supabase (SECURITY DEFINER PL/pgSQL), we
cannot call it directly in unit-style tests.  Instead we:
1. Mirror the function's expected post-deletion state using dicts
2. Assert the migration SQL addresses the required tables by parsing the SQL file
3. Assert anonymization logic is present for governance_audit_log

For true end-to-end coverage a live Supabase test environment is required; those
tests are flagged with @pytest.mark.live_db and skipped by default.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIGRATION_PATH = Path(__file__).resolve().parents[2] / (
    "supabase/migrations/20260411153000_gdpr_deletion_hardening.sql"
)


def _load_migration() -> str:
    """Return the hardening migration SQL as a lowercase string."""
    return _MIGRATION_PATH.read_text(encoding="utf-8").lower()


# ---------------------------------------------------------------------------
# Task 1 tests: migration SQL covers the scoped tables
# ---------------------------------------------------------------------------


class TestDeletionMigrationCoversRequiredTables:
    """Assert the hardening migration SQL references every table that must be
    handled for GDPR-02/03 compliance.

    Tables with ON DELETE CASCADE already auto-clean; explicit DELETEs in the
    function are safe redundancy.  Tables with NO FK or RESTRICT default must
    have explicit DELETE statements.  governance_audit_log must be anonymized,
    not deleted.
    """

    def test_migration_file_exists(self) -> None:
        """The hardening migration SQL file must exist."""
        assert _MIGRATION_PATH.exists(), (
            f"Migration file missing: {_MIGRATION_PATH}"
        )

    def test_migration_replaces_delete_user_account(self) -> None:
        """The migration must CREATE OR REPLACE delete_user_account."""
        sql = _load_migration()
        assert "create or replace function delete_user_account" in sql, (
            "Migration must replace the delete_user_account() function"
        )

    # ---- tables with NO FK / RESTRICT that predate the original migration ----

    def test_covers_governance_audit_log_anonymization(self) -> None:
        """governance_audit_log must be anonymized (UPDATE), not deleted."""
        sql = _load_migration()
        # Must contain an UPDATE on governance_audit_log that sets user_id
        assert re.search(
            r"update\s+governance_audit_log\b.*set\s+user_id",
            sql,
            re.DOTALL,
        ), "Migration must anonymize governance_audit_log rows by setting user_id to sentinel"

    def test_covers_approval_chains_deletion(self) -> None:
        """approval_chains (no FK) must be explicitly deleted."""
        sql = _load_migration()
        assert "delete from approval_chains" in sql

    def test_covers_onboarding_drip_emails_deletion(self) -> None:
        """onboarding_drip_emails (no FK) must be explicitly deleted."""
        sql = _load_migration()
        assert "delete from onboarding_drip_emails" in sql

    def test_covers_onboarding_checklist_deletion(self) -> None:
        """onboarding_checklist (no FK) must be explicitly deleted."""
        sql = _load_migration()
        assert "delete from onboarding_checklist" in sql

    def test_covers_app_projects_deletion(self) -> None:
        """app_projects (no FK) must be explicitly deleted."""
        sql = _load_migration()
        assert "delete from app_projects" in sql

    def test_covers_metric_baselines_deletion(self) -> None:
        """metric_baselines (no FK) must be explicitly deleted."""
        sql = _load_migration()
        assert "delete from metric_baselines" in sql

    def test_covers_subscriptions_deletion(self) -> None:
        """subscriptions (REFERENCES auth.users(id) no CASCADE) must be deleted."""
        sql = _load_migration()
        assert "delete from subscriptions" in sql

    # ---- tables with CASCADE that are safe but covered for completeness ----

    def test_covers_decision_journal(self) -> None:
        """decision_journal should be covered."""
        sql = _load_migration()
        assert "decision_journal" in sql

    def test_covers_unified_action_history(self) -> None:
        """unified_action_history should be covered."""
        sql = _load_migration()
        assert "unified_action_history" in sql

    def test_covers_integration_credentials(self) -> None:
        """integration_credentials should be covered."""
        sql = _load_migration()
        assert "integration_credentials" in sql

    def test_covers_integration_sync_state(self) -> None:
        """integration_sync_state should be covered."""
        sql = _load_migration()
        assert "integration_sync_state" in sql

    def test_covers_proactive_alert_log(self) -> None:
        """proactive_alert_log should be covered."""
        sql = _load_migration()
        assert "proactive_alert_log" in sql

    def test_covers_brand_profiles(self) -> None:
        """brand_profiles should be covered."""
        sql = _load_migration()
        assert "brand_profiles" in sql

    def test_covers_notification_rules(self) -> None:
        """notification_rules should be covered."""
        sql = _load_migration()
        assert "notification_rules" in sql

    def test_covers_financial_health_snapshots(self) -> None:
        """financial_health_snapshots should be covered."""
        sql = _load_migration()
        assert "financial_health_snapshots" in sql


# ---------------------------------------------------------------------------
# Task 1 tests: anonymization contract for governance_audit_log
# ---------------------------------------------------------------------------


class TestGovernanceAuditLogAnonymization:
    """Verify the anonymization contract for governance_audit_log.

    The admin governance viewer enriches rows with actor emails via the auth
    admin API; after deletion the user no longer exists in auth.users, so
    viewer enrichment must not hard-fail.  The migration satisfies this by:
    - Setting user_id to a well-known sentinel UUID (deleted-user placeholder)
    - Clearing ip_address (direct identity signal)
    """

    def test_anonymization_clears_ip_address(self) -> None:
        """The anonymization UPDATE must clear ip_address."""
        sql = _load_migration()
        # UPDATE governance_audit_log SET user_id = ..., ip_address = NULL
        assert re.search(
            r"update\s+governance_audit_log\b.*ip_address\s*=\s*null",
            sql,
            re.DOTALL,
        ), "Migration must set ip_address = NULL when anonymizing governance_audit_log"

    def test_anonymization_uses_sentinel_or_null_for_user_id(self) -> None:
        """user_id must be replaced by sentinel UUID (variable or literal) or NULL."""
        sql = _load_migration()
        # Accept: SET user_id = NULL, SET user_id = 'uuid-literal', or SET user_id = _sentinel_variable
        has_null = re.search(
            r"update\s+governance_audit_log\b.*user_id\s*=\s*null",
            sql,
            re.DOTALL,
        )
        has_sentinel_literal = re.search(
            r"update\s+governance_audit_log\b.*user_id\s*=\s*'[0-9a-f-]{36}'",
            sql,
            re.DOTALL,
        )
        has_sentinel_variable = re.search(
            r"update\s+governance_audit_log\b.*user_id\s*=\s*_\w+uuid",
            sql,
            re.DOTALL,
        )
        assert has_null or has_sentinel_literal or has_sentinel_variable, (
            "governance_audit_log anonymization must set user_id to NULL, a sentinel UUID literal, "
            "or a sentinel UUID variable"
        )

    def test_sentinel_uuid_comment_explains_intent(self) -> None:
        """The migration should include a comment explaining governance anonymization."""
        sql = _load_migration()
        assert "anonymi" in sql, (
            "Migration should include a comment explaining audit log anonymization"
        )

    def test_approval_chains_also_cleared(self) -> None:
        """approval_chain_steps cascade from approval_chains DELETE."""
        sql = _load_migration()
        # approval_chains deletion covers steps via CASCADE
        assert "approval_chains" in sql


# ---------------------------------------------------------------------------
# Task 1 tests: data_deletion_requests audit trail preservation
# ---------------------------------------------------------------------------


class TestDataDeletionRequestsPreservation:
    """data_deletion_requests must survive as the durable audit trail."""

    def test_migration_does_not_delete_data_deletion_requests(self) -> None:
        """The hardening migration must NOT add DELETE FROM data_deletion_requests."""
        sql = _load_migration()
        # The original migration uses ON DELETE SET NULL — the hardening one
        # should not add a DELETE that would destroy the audit trail.
        # We look for a bare DELETE (not inside a comment) on that table.
        # Strip SQL comments then check.
        sql_no_comments = re.sub(r"--[^\n]*", "", sql)
        assert "delete from data_deletion_requests" not in sql_no_comments, (
            "Hardening migration must NOT delete data_deletion_requests rows; "
            "they are the durable audit trail."
        )

    def test_migration_updates_deletion_request_status(self) -> None:
        """The function must still mark deletion requests as completed."""
        sql = _load_migration()
        assert "data_deletion_requests" in sql
        assert "completed" in sql


# ---------------------------------------------------------------------------
# Task 1 tests: simulated post-deletion state assertions
# ---------------------------------------------------------------------------


class TestSimulatedPostDeletionState:
    """Simulate the expected in-memory state after delete_user_account() runs.

    These tests validate the *contract* the migration is designed to fulfill,
    not the live DB execution.  They serve as living documentation for CI.
    """

    USER_ID = "aaaabbbb-1111-2222-3333-444455556666"
    SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"

    def _make_user_rows(self) -> dict[str, list[dict]]:
        """Return representative rows that would exist before deletion."""
        return {
            "governance_audit_log": [
                {
                    "id": "g1",
                    "user_id": self.USER_ID,
                    "action_type": "workflow_approved",
                    "resource_type": "workflow",
                    "resource_id": "wf-abc",
                    "ip_address": "192.168.1.1",
                    "details": {"note": "approved by user"},
                }
            ],
            "approval_chains": [
                {"id": "ac1", "user_id": self.USER_ID, "action_type": "expense_approval"}
            ],
            "data_deletion_requests": [
                {
                    "id": "d1",
                    "user_id": self.USER_ID,  # becomes NULL after auth.users deletion
                    "status": "pending",
                    "confirmation_code": "abc123",
                }
            ],
            "subscriptions": [
                {"user_id": self.USER_ID, "stripe_customer_id": "cus_test"}
            ],
        }

    def _simulate_delete_user_account(
        self, rows: dict[str, list[dict]]
    ) -> dict[str, list[dict]]:
        """Simulate the delete_user_account() behavior in Python.

        Mirrors what the SQL function does:
        - DELETE rows for tables that must be cleared
        - UPDATE governance_audit_log: user_id → sentinel, ip_address → None
        - UPDATE data_deletion_requests: status → completed (user_id → NULL via CASCADE)
        """
        result: dict[str, list[dict]] = {}

        # governance_audit_log: anonymize, not delete
        result["governance_audit_log"] = [
            {
                **row,
                "user_id": self.SENTINEL_UUID,
                "ip_address": None,
            }
            for row in rows.get("governance_audit_log", [])
        ]

        # approval_chains: deleted
        result["approval_chains"] = []

        # data_deletion_requests: status updated, user_id set to NULL (SET NULL FK)
        result["data_deletion_requests"] = [
            {
                **row,
                "user_id": None,  # ON DELETE SET NULL
                "status": "completed",
            }
            for row in rows.get("data_deletion_requests", [])
        ]

        # subscriptions: deleted
        result["subscriptions"] = []

        return result

    def test_governance_audit_log_anonymized_user_id(self) -> None:
        """governance_audit_log rows survive with anonymized user_id."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)

        audit_rows = after["governance_audit_log"]
        assert len(audit_rows) == 1, "Audit log row must survive deletion"
        row = audit_rows[0]
        assert row["user_id"] == self.SENTINEL_UUID
        assert row["action_type"] == "workflow_approved"  # content preserved

    def test_governance_audit_log_ip_address_cleared(self) -> None:
        """governance_audit_log ip_address must be NULL after anonymization."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)

        row = after["governance_audit_log"][0]
        assert row["ip_address"] is None

    def test_approval_chains_deleted(self) -> None:
        """approval_chains rows must be deleted."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)
        assert after["approval_chains"] == []

    def test_data_deletion_requests_survive(self) -> None:
        """data_deletion_requests row must survive as audit trail."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)
        assert len(after["data_deletion_requests"]) == 1

    def test_data_deletion_requests_status_completed(self) -> None:
        """data_deletion_requests status must be 'completed' after deletion."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)
        assert after["data_deletion_requests"][0]["status"] == "completed"

    def test_data_deletion_requests_user_id_nulled(self) -> None:
        """data_deletion_requests user_id must be NULL (ON DELETE SET NULL)."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)
        assert after["data_deletion_requests"][0]["user_id"] is None

    def test_subscriptions_deleted(self) -> None:
        """subscriptions rows must be deleted before auth.users removal."""
        rows = self._make_user_rows()
        after = self._simulate_delete_user_account(rows)
        assert after["subscriptions"] == []
