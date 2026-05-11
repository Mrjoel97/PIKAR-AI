# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Verify OutcomeSummaryWorker upgrades status outcomes to LLM outcomes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.outcome_summary_worker import OutcomeSummaryWorker


@pytest.mark.asyncio
async def test_worker_upgrades_pending_outcome_to_llm():
    pending_step = {
        "id": "s1",
        "status": "completed",
        "tool_name": "fetch_rows",
        "output_data": {"rows": [1, 2, 3]},
        "outcome_text": None,
        "outcome_source": None,
    }
    fake_client = MagicMock()

    # Mock the select chain (.select.eq.is_) used to find pending steps
    select_chain = fake_client.table.return_value.select.return_value.eq.return_value.is_
    select_chain.return_value = MagicMock(data=[pending_step])

    # Mock the update chain (.update.eq) used to write the LLM summary
    update_chain = fake_client.table.return_value.update.return_value.eq

    with patch(
        "app.workflows.outcome_summary_worker._summarize",
        new=AsyncMock(return_value="Fetched 3 rows of recent sign-ups."),
    ), patch(
        "app.workflows.outcome_summary_worker.execute_async",
        new=AsyncMock(
            side_effect=[
                MagicMock(data=[pending_step]),  # for the SELECT
                MagicMock(data=[{}]),  # for the UPDATE
            ]
        ),
    ):
        worker = OutcomeSummaryWorker(client=fake_client)
        n = await worker.run_once(limit=10)

    assert n == 1


@pytest.mark.asyncio
async def test_worker_no_op_on_empty_batch():
    fake_client = MagicMock()
    with patch(
        "app.workflows.outcome_summary_worker.execute_async",
        new=AsyncMock(return_value=MagicMock(data=[])),
    ):
        worker = OutcomeSummaryWorker(client=fake_client)
        n = await worker.run_once(limit=10)
    assert n == 0


@pytest.mark.asyncio
async def test_worker_skips_step_when_llm_fails():
    pending_step = {
        "id": "s2",
        "status": "completed",
        "tool_name": "send_email",
        "output_data": {},
        "outcome_text": None,
        "outcome_source": None,
    }
    fake_client = MagicMock()
    with patch(
        "app.workflows.outcome_summary_worker._summarize",
        new=AsyncMock(return_value=None),  # LLM returned no text
    ), patch(
        "app.workflows.outcome_summary_worker.execute_async",
        new=AsyncMock(return_value=MagicMock(data=[pending_step])),
    ):
        worker = OutcomeSummaryWorker(client=fake_client)
        n = await worker.run_once(limit=10)
    # LLM produced nothing → no upgrade, but no crash either
    assert n == 0
