"""Integration tests for the workflow_template_versioning migration.

These tests verify that the 20260615000000 migration:
  1. Creates the ``workflow_template_versions`` table and it is selectable.
  2. Adds ``workflow_templates.current_version_id`` (selectable).
  3. Adds ``workflow_executions.template_version_id`` (selectable).
  4. Backfills a v1 row for every workflow_templates row whose Phase 109
     graph_nodes projection succeeded (graph_nodes IS NOT NULL).
  5. Leaves current_version_id NULL for rows whose graph_nodes is NULL.
  6. Leaves legacy workflow_executions rows with NULL template_version_id
     (they predate the migration).
  7. Preserves the legacy ``workflow_executions.template_version INT`` column
     alongside the new ``template_version_id UUID`` column — both nullable,
     both queryable. This is the B-6 fix from plan-checker iteration 1; it
     catches any future migration that accidentally drops the legacy column.

Pattern follows tests/integration/test_workflow_template_graph_projection.py
(Phase 109's pattern) — uses the Supabase service client against a real local
database, skips when SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not
configured. Per project memory, integration tests must hit a real database,
not mocks.

Run requirements
----------------
    supabase start                          # local stack must be up
    supabase db reset --local               # ensures migration chain applied
    export SUPABASE_URL=...                 # service-role creds
    export SUPABASE_SERVICE_ROLE_KEY=...
    uv run pytest tests/integration/test_workflow_template_versioning_migration.py -v

Without those env vars the suite SKIPS cleanly (CI without local Supabase
shows seven skipped, zero failures).
"""

from __future__ import annotations

import os
from typing import Any

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def supabase_client() -> Any:
    """Service-role Supabase client for migration-level inspection."""
    try:
        from app.services.supabase_client import get_supabase_client

        return get_supabase_client()
    except Exception:
        pytest.skip("Supabase not available")


# ---------------------------------------------------------------------------
# Schema-shape tests
# ---------------------------------------------------------------------------


def test_workflow_template_versions_table_exists(supabase_client: Any) -> None:
    """The new workflow_template_versions table is selectable via PostgREST.

    A successful round-trip of select("id").limit(1) implies the migration's
    CREATE TABLE IF NOT EXISTS statement ran and the table is exposed via
    the PostgREST schema cache.
    """
    response = (
        supabase_client.table("workflow_template_versions")
        .select("id")
        .limit(1)
        .execute()
    )
    assert response is not None, "Selecting from workflow_template_versions failed"


def test_current_version_id_column_exists(supabase_client: Any) -> None:
    """workflow_templates.current_version_id column is selectable.

    If the ALTER TABLE ADD COLUMN IF NOT EXISTS statement had been skipped or
    rolled back, this select would return a PostgREST 400 schema error.
    """
    response = (
        supabase_client.table("workflow_templates")
        .select("id, current_version_id")
        .limit(1)
        .execute()
    )
    assert response is not None, "Selecting workflow_templates.current_version_id failed"


def test_template_version_id_column_exists(supabase_client: Any) -> None:
    """workflow_executions.template_version_id column is selectable.

    Verifies the new UUID column shipped by task 01-02 is reachable.
    """
    response = (
        supabase_client.table("workflow_executions")
        .select("id, template_version_id")
        .limit(1)
        .execute()
    )
    assert response is not None, (
        "Selecting workflow_executions.template_version_id failed"
    )


# ---------------------------------------------------------------------------
# Backfill tests
# ---------------------------------------------------------------------------


def test_backfill_populates_v1_for_graph_projected_templates(
    supabase_client: Any,
) -> None:
    """Every workflow_templates row with graph_nodes NOT NULL has a v1 version.

    Asserts the Phase 110 backfill DO block ran for every row whose Phase 109
    projection succeeded: current_version_id is non-NULL, a corresponding
    workflow_template_versions row exists with version_number = 1,
    parent_version_id IS NULL, and the comment starts with the backfill
    marker prose.
    """
    projected_rows = (
        supabase_client.table("workflow_templates")
        .select("id, current_version_id, graph_nodes")
        .not_.is_("graph_nodes", "null")
        .limit(50)
        .execute()
    )
    rows = projected_rows.data or []
    if not rows:
        pytest.skip(
            "No workflow_templates with non-NULL graph_nodes in this DB; "
            "Phase 109 projection has nothing to backfill"
        )

    for row in rows:
        assert row["current_version_id"] is not None, (
            f"Template {row['id']} has non-NULL graph_nodes but NULL "
            f"current_version_id — backfill missed it"
        )

    # For one such row, fetch its v1 record and assert backfill markers.
    sample = rows[0]
    version_resp = (
        supabase_client.table("workflow_template_versions")
        .select("*")
        .eq("template_id", sample["id"])
        .eq("version_number", 1)
        .execute()
    )
    assert version_resp.data, (
        f"No v1 row in workflow_template_versions for template {sample['id']}"
    )
    v1 = version_resp.data[0]
    assert v1["parent_version_id"] is None, "Backfilled v1 must have NULL parent"
    assert v1["comment"] is not None and v1["comment"].startswith(
        "Phase 110 backfill"
    ), f"v1 comment does not start with expected backfill marker: {v1['comment']!r}"


def test_backfill_skips_null_graph_rows(supabase_client: Any) -> None:
    """Rows with graph_nodes IS NULL are not backfilled (Plan 02 handles them).

    The migration's WHERE graph_nodes IS NOT NULL filter scopes the backfill
    to projected rows only; the empty-phases sentinel rows stay with
    current_version_id NULL until first Edit (Plan 02).
    """
    null_rows = (
        supabase_client.table("workflow_templates")
        .select("id, current_version_id, graph_nodes")
        .is_("graph_nodes", "null")
        .limit(50)
        .execute()
    )
    rows = null_rows.data or []
    if not rows:
        pytest.skip("No workflow_templates with NULL graph_nodes in this DB")

    for row in rows:
        assert row["current_version_id"] is None, (
            f"Template {row['id']} has NULL graph_nodes but non-NULL "
            f"current_version_id — backfill should have skipped it"
        )


def test_legacy_workflow_executions_keep_null_template_version_id(
    supabase_client: Any,
) -> None:
    """Pre-existing workflow_executions stay with NULL template_version_id.

    Phase 110 only adds the column; Plan 02 will start writing it on new
    executions. Until Plan 02 ships, every existing execution must have a
    NULL value (no legacy execution should magically be pinned to a
    backfilled v1 row).
    """
    rows_resp = (
        supabase_client.table("workflow_executions")
        .select("id, template_version_id, template_version")
        .limit(100)
        .execute()
    )
    rows = rows_resp.data or []
    if not rows:
        pytest.skip("No workflow_executions rows present in this DB")

    pinned = [r for r in rows if r.get("template_version_id") is not None]
    assert not pinned, (
        f"Found {len(pinned)} workflow_executions rows with non-NULL "
        f"template_version_id — Plan 02 has not shipped yet, no row should be "
        f"pinned. Examples: {pinned[:3]}"
    )


# ---------------------------------------------------------------------------
# Legacy-column preservation test (B-6 fix from plan-checker iteration 1)
# ---------------------------------------------------------------------------


def test_legacy_template_version_int_column_preserved(supabase_client: Any) -> None:
    """Legacy ``workflow_executions.template_version`` INT column is preserved.

    Phase 110 adds ``template_version_id UUID`` but MUST NOT drop the legacy
    ``template_version INT`` column from 0051 — both columns coexist until a
    future cleanup migration. This test is a regression-guard that catches
    any future migration which accidentally drops the legacy column.

    Strategy: select both columns from workflow_executions. If either column
    is missing, PostgREST returns a 400 schema error and the test fails. We
    additionally verify that, for any existing row, the legacy column is
    typed as an integer (or NULL) and the new column is UUID-shaped (or
    NULL).
    """
    response = (
        supabase_client.table("workflow_executions")
        .select("id, template_version, template_version_id")
        .limit(20)
        .execute()
    )
    assert response is not None, (
        "Selecting both template_version + template_version_id failed — one of "
        "the columns is missing"
    )

    rows = response.data or []
    if not rows:
        # No rows to inspect, but the SELECT itself proved both columns are
        # wired and addressable. That alone satisfies the preservation
        # contract for this test.
        return

    for row in rows:
        legacy = row.get("template_version")
        new_uuid = row.get("template_version_id")

        # Legacy column must be NULL or an integer (PostgREST returns ints
        # as Python ints; bools are a subclass of int so reject explicitly).
        assert legacy is None or (isinstance(legacy, int) and not isinstance(legacy, bool)), (
            f"workflow_executions.template_version expected int|None, got "
            f"{type(legacy).__name__}={legacy!r}"
        )

        # New column must be NULL or a UUID-shaped string (PostgREST
        # serialises uuid as the canonical 36-character form). We only
        # check the length+dash positions; full UUID parsing is overkill.
        if new_uuid is not None:
            assert isinstance(new_uuid, str), (
                f"template_version_id expected str|None, got "
                f"{type(new_uuid).__name__}={new_uuid!r}"
            )
            assert len(new_uuid) == 36 and new_uuid[8] == "-" and new_uuid[13] == "-", (
                f"template_version_id does not match UUID shape: {new_uuid!r}"
            )
