# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for ``app.agents.runtime.handoff``.

Covers Tasks 28 + 42 of the agent operating model W1+W2 plan:
  - Task 28: ``record_handoff`` writes a row to ``initiative_phase_history``
    when an initiative is in scope, skips quietly when it isn't, and
    swallows DB errors instead of breaking the turn.
  - Task 42: the row payload preserves every field of a real ``HandoffPacket``
    (``model_dump`` round-trip), and the ``_to_dict`` fallback chain handles
    dict-like and ``vars()``-only carriers without raising.
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the google.adk surface the same way the rest of the unit suite does so
# importing ``app.agents.handoff_packet`` (and anything it touches) does not
# require the real ADK.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.adk.tools.tool_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _packet(
    target: str = "FinancialAnalysisAgent",
    source: str = "executive",
) -> MagicMock:
    """Build a MagicMock that quacks like a HandoffPacket."""
    p = MagicMock()
    p.source_agent = source
    p.target_agent = target
    p.intent = "Forecast Q3"
    p.correlation_id = "corr-1"
    p.model_dump.return_value = {
        "source_agent": source,
        "target_agent": target,
        "intent": "Forecast Q3",
        "correlation_id": "corr-1",
    }
    return p


def _supabase_table_chain(execute_return: object) -> MagicMock:
    """Build a Supabase client whose ``table().insert().execute()`` is awaitable."""
    client = MagicMock()
    table = MagicMock()
    insert = MagicMock()
    execute = AsyncMock(return_value=execute_return)
    insert.execute = execute
    table.insert.return_value = insert
    client.table.return_value = table
    return client


# ---------------------------------------------------------------------------
# Task 28 — module + history-row writer
# ---------------------------------------------------------------------------


def test_record_handoff_inserts_row_when_initiative_present():
    from app.agents.runtime import handoff

    inserted_row = MagicMock(data=[{"id": "row-1"}])
    fake_client = _supabase_table_chain(inserted_row)
    get_client = AsyncMock(return_value=fake_client)

    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is not None
    fake_client.table.assert_called_once_with("initiative_phase_history")
    fake_client.table().insert.assert_called_once()
    payload = fake_client.table().insert.call_args.args[0]
    assert payload["initiative_id"] == "init-X"
    assert payload["phase"] == "validation"
    assert payload["event"] == "handoff"
    assert payload["from_agent"] == "executive"
    assert payload["to_agent"] == "FinancialAnalysisAgent"
    assert payload["packet_id"] == packet_id
    # The serialized packet body is included verbatim.
    assert payload["packet"]["target_agent"] == "FinancialAnalysisAgent"


def test_record_handoff_skips_when_no_initiative():
    from app.agents.runtime import handoff

    get_client = AsyncMock()
    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id=None,
                phase=None,
            )
        )

    assert packet_id is None
    get_client.assert_not_awaited()


def test_record_handoff_swallows_db_errors():
    from app.agents.runtime import handoff

    get_client = AsyncMock(side_effect=RuntimeError("db down"))
    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is None


def test_record_handoff_swallows_insert_errors():
    """Even after the client is acquired, a failing insert must not raise."""
    from app.agents.runtime import handoff

    client = MagicMock()
    insert = MagicMock()
    insert.execute = AsyncMock(side_effect=RuntimeError("insert exploded"))
    client.table.return_value.insert.return_value = insert
    get_client = AsyncMock(return_value=client)

    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is None


# ---------------------------------------------------------------------------
# Task 42 — model_dump fallback / packet serialization
# ---------------------------------------------------------------------------


def test_record_handoff_serializes_real_packet():
    """A real ``HandoffPacket`` round-trips through the row payload without loss."""
    from app.agents.handoff_packet import HandoffPacket
    from app.agents.runtime import handoff

    packet = HandoffPacket(
        intent="Forecast Q3",
        evidence=["last call mentioned Q3 plan"],
        constraints=["due Friday"],
        expected_output_shape="text",
        source_agent="executive",
        target_agent="FinancialAnalysisAgent",
        correlation_id="corr-1",
    )

    fake_client = _supabase_table_chain(MagicMock(data=[{"id": "row-1"}]))
    get_client = AsyncMock(return_value=fake_client)

    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=packet,
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is not None
    payload = fake_client.table().insert.call_args.args[0]
    assert payload["from_agent"] == "executive"
    assert payload["to_agent"] == "FinancialAnalysisAgent"
    assert payload["packet"]["intent"] == "Forecast Q3"
    assert payload["packet"]["evidence"] == ["last call mentioned Q3 plan"]
    assert payload["packet"]["constraints"] == ["due Friday"]
    assert payload["packet"]["target_agent"] == "FinancialAnalysisAgent"
    assert payload["packet"]["expected_output_shape"] == "text"
    assert payload["packet"]["correlation_id"] == "corr-1"


def test_to_dict_falls_back_to_dict_cast_when_model_dump_missing():
    """Packets that don't expose ``model_dump`` should still serialize cleanly."""
    from app.agents.runtime.handoff import _to_dict

    raw = {
        "source_agent": "executive",
        "target_agent": "MarketingAgent",
        "intent": "Plan launch",
    }
    assert _to_dict(raw) == raw


def test_to_dict_falls_back_to_vars_for_plain_objects():
    """Plain ``object``-style carriers (no ``model_dump``, no Mapping) use vars()."""
    from app.agents.runtime.handoff import _to_dict

    class _BareCarrier:
        def __init__(self):
            self.source_agent = "executive"
            self.target_agent = "OperationsAgent"
            self.intent = "Run audit"

    result = _to_dict(_BareCarrier())
    assert result == {
        "source_agent": "executive",
        "target_agent": "OperationsAgent",
        "intent": "Run audit",
    }


def test_to_dict_returns_empty_when_every_strategy_fails():
    """When nothing works, ``_to_dict`` returns ``{}`` instead of raising."""
    from app.agents.runtime.handoff import _to_dict

    class _Opaque:
        __slots__ = ()  # no __dict__ → vars() will raise

        def __iter__(self):
            raise TypeError("not iterable")

    assert _to_dict(_Opaque()) == {}


def test_record_handoff_with_dict_packet_still_writes_row():
    """End-to-end: a dict-shaped packet flows through the full path."""
    from app.agents.runtime import handoff

    raw_packet = {
        "source_agent": "executive",
        "target_agent": "DataAgent",
        "intent": "Pull metrics",
    }
    fake_client = _supabase_table_chain(MagicMock(data=[{"id": "row-2"}]))
    get_client = AsyncMock(return_value=fake_client)

    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=raw_packet,  # type: ignore[arg-type]
                initiative_id="init-Y",
                phase="build",
            )
        )

    assert packet_id is not None
    payload = fake_client.table().insert.call_args.args[0]
    # Dict-shaped packets don't expose getattr fields, so from/to_agent come
    # via the subscript fallback in ``_get_field``.
    assert payload["from_agent"] == "executive"
    assert payload["to_agent"] == "DataAgent"
    assert payload["packet"]["intent"] == "Pull metrics"
