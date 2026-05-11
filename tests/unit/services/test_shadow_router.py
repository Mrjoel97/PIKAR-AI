# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ``app.services.shadow_router``.

Covers the three divergence dimensions (text / tool_calls / artifacts),
the ``should_shadow`` sampler, and the fire-and-forget Supabase
persistence. See ``project_agent_operating_model_w1.md`` for design
context.
"""

from __future__ import annotations

import asyncio
import logging
import random
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services import shadow_router
from app.services.shadow_router import (
    ShadowOutput,
    compute_divergence,
    fire_and_forget_diff_write,
    should_shadow,
    write_shadow_diff,
)

# ---------------------------------------------------------------------------
# compute_divergence — text dimension
# ---------------------------------------------------------------------------


def test_compute_divergence_identical_text_returns_zero() -> None:
    primary = ShadowOutput(text="The quick brown fox jumps over the lazy dog.")
    candidate = ShadowOutput(text="The quick brown fox jumps over the lazy dog.")

    div = compute_divergence(primary, candidate)

    assert div.text_score == 0.0
    assert div.kind == "identical"
    assert div.score == 0.0


def test_compute_divergence_completely_different_text_returns_one() -> None:
    primary = ShadowOutput(text="alpha beta gamma delta")
    candidate = ShadowOutput(text="omega psi chi phi")

    div = compute_divergence(primary, candidate)

    assert div.text_score == 1.0
    assert div.kind == "text"
    assert div.score == 1.0


def test_compute_divergence_partial_text_overlap() -> None:
    # Two of four tokens overlap → Jaccard distance is strictly between 0 and 1.
    primary = ShadowOutput(text="alpha beta gamma delta")
    candidate = ShadowOutput(text="alpha beta epsilon zeta")

    div = compute_divergence(primary, candidate)

    assert 0.0 < div.text_score < 1.0


def test_compute_divergence_empty_both_texts_treated_as_identical() -> None:
    primary = ShadowOutput(text="")
    candidate = ShadowOutput(text="")

    div = compute_divergence(primary, candidate)

    assert div.text_score == 0.0
    assert div.kind == "identical"


def test_compute_divergence_one_empty_text() -> None:
    primary = ShadowOutput(text="")
    candidate = ShadowOutput(text="alpha beta gamma")

    div = compute_divergence(primary, candidate)

    assert div.text_score == 1.0
    assert div.kind == "text"


def test_compute_divergence_text_normalizes_case_and_punctuation() -> None:
    primary = ShadowOutput(text="Hello, world!")
    candidate = ShadowOutput(text="hello world")

    div = compute_divergence(primary, candidate)

    assert div.text_score == 0.0
    assert div.kind == "identical"


def test_compute_divergence_text_skips_short_tokens() -> None:
    # Length-1 tokens ("I") must be dropped before computing similarity.
    # primary tokens (>=2): {"am", "here"}; candidate tokens: {"you", "are", "here"}.
    # Intersection: {"here"} (1); union: {"am", "here", "you", "are"} (4).
    # Distance: 1 - 1/4 = 0.75.
    primary = ShadowOutput(text="I am here")
    candidate = ShadowOutput(text="you are here")

    div = compute_divergence(primary, candidate)

    assert div.text_score == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# compute_divergence — tool_calls dimension
# ---------------------------------------------------------------------------


def test_compute_divergence_tool_calls_same_multiset_zero_regardless_of_order() -> None:
    call_a = {"tool_id": "search_web", "args": {"query": "hello"}}
    call_b = {"tool_id": "send_email", "args": {"to": "a@b.com", "body": "hi"}}

    primary = ShadowOutput(tool_calls=[call_a, call_b])
    candidate = ShadowOutput(tool_calls=[call_b, call_a])

    div = compute_divergence(primary, candidate)

    assert div.tool_calls_score == 0.0


def test_compute_divergence_tool_calls_different_args_diverge() -> None:
    primary = ShadowOutput(
        tool_calls=[{"tool_id": "search_web", "args": {"query": "alpha"}}]
    )
    candidate = ShadowOutput(
        tool_calls=[{"tool_id": "search_web", "args": {"query": "beta"}}]
    )

    div = compute_divergence(primary, candidate)

    assert div.tool_calls_score > 0.0


def test_compute_divergence_tool_calls_subset_partial_score() -> None:
    # Primary has two calls, candidate has one of them.
    call_a = {"tool_id": "search_web", "args": {"query": "hello"}}
    call_b = {"tool_id": "send_email", "args": {"to": "x@y.com"}}

    primary = ShadowOutput(tool_calls=[call_a, call_b])
    candidate = ShadowOutput(tool_calls=[call_a])

    div = compute_divergence(primary, candidate)

    assert 0.0 < div.tool_calls_score < 1.0


# ---------------------------------------------------------------------------
# compute_divergence — artifacts dimension
# ---------------------------------------------------------------------------


def test_compute_divergence_artifacts_same_set_zero() -> None:
    primary = ShadowOutput(
        artifacts=[
            {"kind": "chart", "content_id": "abc"},
            {"kind": "doc", "content_id": "def"},
        ]
    )
    candidate = ShadowOutput(
        artifacts=[
            {"kind": "doc", "content_id": "def"},
            {"kind": "chart", "content_id": "abc"},
        ]
    )

    div = compute_divergence(primary, candidate)

    assert div.artifacts_score == 0.0


def test_compute_divergence_artifacts_disjoint_one() -> None:
    primary = ShadowOutput(artifacts=[{"kind": "chart", "content_id": "abc"}])
    candidate = ShadowOutput(artifacts=[{"kind": "chart", "content_id": "xyz"}])

    div = compute_divergence(primary, candidate)

    assert div.artifacts_score == 1.0


# ---------------------------------------------------------------------------
# compute_divergence — overall score + kind
# ---------------------------------------------------------------------------


def test_compute_divergence_overall_score_is_max_of_dimensions() -> None:
    # text fully diverges (1.0), tool_calls and artifacts agree (0.0).
    primary = ShadowOutput(
        text="alpha beta",
        tool_calls=[{"tool_id": "noop", "args": {}}],
        artifacts=[{"kind": "doc", "content_id": "1"}],
    )
    candidate = ShadowOutput(
        text="omega psi",
        tool_calls=[{"tool_id": "noop", "args": {}}],
        artifacts=[{"kind": "doc", "content_id": "1"}],
    )

    div = compute_divergence(primary, candidate)

    assert div.text_score == 1.0
    assert div.tool_calls_score == 0.0
    assert div.artifacts_score == 0.0
    assert div.score == 1.0
    assert div.kind == "text"


def test_compute_divergence_multiple_dimensions_diverge_yields_multiple_kind() -> None:
    primary = ShadowOutput(
        text="alpha beta",
        tool_calls=[{"tool_id": "search_web", "args": {"q": "alpha"}}],
        artifacts=[{"kind": "doc", "content_id": "1"}],
    )
    candidate = ShadowOutput(
        text="omega psi",
        tool_calls=[{"tool_id": "send_email", "args": {"to": "x@y.com"}}],
        artifacts=[{"kind": "doc", "content_id": "1"}],
    )

    div = compute_divergence(primary, candidate)

    assert div.text_score > 0
    assert div.tool_calls_score > 0
    assert div.kind == "multiple"


# ---------------------------------------------------------------------------
# should_shadow
# ---------------------------------------------------------------------------


def test_should_shadow_zero_percent_never_returns_true() -> None:
    assert not any(should_shadow(0) for _ in range(1000))


def test_should_shadow_hundred_percent_always_returns_true() -> None:
    assert all(should_shadow(100) for _ in range(1000))


def test_should_shadow_fifty_percent_roughly_half_true() -> None:
    random.seed(42)  # Stabilize against rare CI flakes.
    count_true = sum(1 for _ in range(1000) if should_shadow(50))
    assert 400 < count_true < 600


def test_should_shadow_clamps_out_of_range_percent() -> None:
    assert not any(should_shadow(-5) for _ in range(100))
    assert all(should_shadow(150) for _ in range(100))


@pytest.mark.parametrize("bad_input", ["10", None, 0.5, 50.0, [], {}, object()])
def test_should_shadow_rejects_non_int_input(bad_input) -> None:
    # Must not raise; must return False for everything that isn't a plain int.
    assert should_shadow(bad_input) is False


def test_should_shadow_rejects_bool_input() -> None:
    # ``bool`` is a subclass of int in Python; we explicitly reject it
    # so callers can't accidentally pass True/False and get 100%/0%.
    assert should_shadow(True) is False
    assert should_shadow(False) is False


# ---------------------------------------------------------------------------
# write_shadow_diff + fire_and_forget_diff_write
# ---------------------------------------------------------------------------


def _make_supabase_mock() -> tuple[MagicMock, MagicMock]:
    """Return ``(client, table_mock)`` shaped like a Supabase async client."""
    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": "row-1"}]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    return client, table_mock


@pytest.mark.asyncio
async def test_write_shadow_diff_calls_supabase_insert_with_record(
    monkeypatch,
) -> None:
    client, table_mock = _make_supabase_mock()
    monkeypatch.setattr(shadow_router, "_get_supabase", lambda: client)

    user_id = uuid4()
    request_id = uuid4()

    primary = ShadowOutput(
        text="hello",
        tool_calls=[{"tool_id": "noop", "args": {}}],
        artifacts=[{"kind": "doc", "content_id": "1"}],
        latency_ms=120,
    )
    candidate = ShadowOutput(
        text="hi",
        tool_calls=[],
        artifacts=[],
        latency_ms=150,
    )
    divergence = compute_divergence(primary, candidate)

    await write_shadow_diff(
        agent_id="executive",
        primary_variant="legacy",
        candidate_variant="manifest",
        primary=primary,
        candidate=candidate,
        divergence=divergence,
        user_id=user_id,
        request_id=request_id,
    )

    # Insert was issued against the correct table with the expected fields.
    assert client.table.call_args[0][0] == "agent_shadow_diffs"
    payload = table_mock.insert.call_args[0][0]
    assert payload["agent_id"] == "executive"
    assert payload["primary_variant"] == "legacy"
    assert payload["candidate_variant"] == "manifest"
    assert payload["primary_text"] == "hello"
    assert payload["candidate_text"] == "hi"
    assert payload["primary_tool_calls"] == [{"tool_id": "noop", "args": {}}]
    assert payload["candidate_tool_calls"] == []
    assert payload["primary_artifacts"] == [{"kind": "doc", "content_id": "1"}]
    assert payload["candidate_artifacts"] == []
    assert payload["divergence_score"] == divergence.score
    assert payload["divergence_kind"] == divergence.kind
    assert payload["primary_latency_ms"] == 120
    assert payload["candidate_latency_ms"] == 150
    assert payload["user_id"] == str(user_id)
    assert payload["request_id"] == str(request_id)


@pytest.mark.asyncio
async def test_write_shadow_diff_omits_optional_ids_when_absent(
    monkeypatch,
) -> None:
    client, table_mock = _make_supabase_mock()
    monkeypatch.setattr(shadow_router, "_get_supabase", lambda: client)

    primary = ShadowOutput(text="a")
    candidate = ShadowOutput(text="a")
    divergence = compute_divergence(primary, candidate)

    await write_shadow_diff(
        agent_id="executive",
        primary_variant="legacy",
        candidate_variant="manifest",
        primary=primary,
        candidate=candidate,
        divergence=divergence,
    )

    payload = table_mock.insert.call_args[0][0]
    # Schema treats user_id/request_id as nullable; we omit the keys
    # entirely when not provided so Supabase uses the column defaults.
    assert "user_id" not in payload
    assert "request_id" not in payload


@pytest.mark.asyncio
async def test_write_shadow_diff_swallows_supabase_exception(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(side_effect=RuntimeError("boom"))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(shadow_router, "_get_supabase", lambda: client)

    primary = ShadowOutput(text="a")
    candidate = ShadowOutput(text="b")
    divergence = compute_divergence(primary, candidate)

    with caplog.at_level(logging.WARNING, logger=shadow_router.logger.name):
        result = await write_shadow_diff(
            agent_id="executive",
            primary_variant="legacy",
            candidate_variant="manifest",
            primary=primary,
            candidate=candidate,
            divergence=divergence,
        )

    assert result is None
    assert any(
        "write_shadow_diff failed" in rec.getMessage() and "boom" in rec.getMessage()
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_write_shadow_diff_swallows_client_acquisition_error(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Even if obtaining the client raises, the helper must not propagate."""

    def explode() -> None:
        raise RuntimeError("no client today")

    monkeypatch.setattr(shadow_router, "_get_supabase", explode)

    primary = ShadowOutput(text="a")
    candidate = ShadowOutput(text="b")
    divergence = compute_divergence(primary, candidate)

    with caplog.at_level(logging.WARNING, logger=shadow_router.logger.name):
        await write_shadow_diff(
            agent_id="executive",
            primary_variant="legacy",
            candidate_variant="manifest",
            primary=primary,
            candidate=candidate,
            divergence=divergence,
        )

    assert any("write_shadow_diff failed" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_fire_and_forget_diff_write_returns_task_immediately(
    monkeypatch,
) -> None:
    client, _ = _make_supabase_mock()
    monkeypatch.setattr(shadow_router, "_get_supabase", lambda: client)

    primary = ShadowOutput(text="a")
    candidate = ShadowOutput(text="a")
    divergence = compute_divergence(primary, candidate)

    task = fire_and_forget_diff_write(
        agent_id="executive",
        primary_variant="legacy",
        candidate_variant="manifest",
        primary=primary,
        candidate=candidate,
        divergence=divergence,
    )

    assert isinstance(task, asyncio.Task)
    # Awaiting the task must not raise — write_shadow_diff swallows all.
    await task
    assert task.done()
    assert task.exception() is None
