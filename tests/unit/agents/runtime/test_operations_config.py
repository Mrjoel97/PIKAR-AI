# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""OperationsConfig — strict per-agent YAML schema with sensible defaults."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

FIX = Path(__file__).parent / "fixtures"


def test_minimal_yaml_loads_with_defaults():
    from app.agents.runtime.operations_config import OperationsConfig

    cfg = OperationsConfig.load(FIX / "operations_minimal.yaml")

    assert cfg.agent_id == "minimal"
    # Sensible defaults must be populated so simple agents need almost no YAML.
    assert cfg.model.primary == "gemini-2.5-pro"
    assert cfg.model.fallback == "gemini-2.5-flash"
    assert cfg.retry.max_attempts == 5
    assert cfg.retry.backoff_initial_s == 2.0
    assert cfg.retry.backoff_multiplier == 2.0
    assert cfg.retry.backoff_max_s == 60.0
    assert cfg.approval.required_above_usd is None
    assert cfg.approval.required_for_external_send is False
    assert cfg.research.max_iterations == 3
    assert cfg.research.required_source_min == 3
    assert cfg.audit.fail_on_any_unmet_criterion is True
    assert cfg.audit.escalate_on_partial is False
    assert cfg.skills.allowed_ids == ["*"]
    assert cfg.skills.injection.top_k == 5
    assert 0 < cfg.skills.injection.similarity_floor <= 1
    assert cfg.skills.injection.similarity_floor == 0.65
    assert cfg.initiative.phases_owned == []
    assert cfg.initiative.can_advance_phase is False
    assert cfg.initiative.can_close is False
    assert cfg.memory.history_retention_months == 18
    assert cfg.memory.retrieval_top_k == 4
    assert cfg.compaction.trigger_token_count == 80_000
    assert cfg.compaction.keep_last_n_turns == 12
    assert cfg.routing.last_resort_default == "direct"


def test_financial_yaml_overrides_defaults():
    from app.agents.runtime.operations_config import OperationsConfig

    cfg = OperationsConfig.load(FIX / "operations_financial.yaml")

    assert cfg.agent_id == "financial"
    assert cfg.model.primary == "gemini-2.5-pro"
    assert cfg.model.fallback == "gemini-2.5-flash"
    assert cfg.approval.required_above_usd == 1000
    assert cfg.approval.required_for_external_send is True
    assert cfg.skills.allowed_ids == [
        "finance:*",
        "data:*",
        "compliance:legal-risk-assessment",
    ]
    assert cfg.initiative.phases_owned == ["validation", "build"]
    assert cfg.initiative.can_advance_phase is True
    assert cfg.initiative.can_close is False
    assert cfg.memory.history_retention_months == 18
    assert cfg.compaction.trigger_token_count == 80_000
    assert cfg.routing.last_resort_default == "initiative"


def test_missing_agent_id_fails_fast(tmp_path: Path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text("model:\n  primary: gemini-2.5-flash\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_unknown_top_level_key_fails_fast(tmp_path: Path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text("agent_id: x\nmystery_section:\n  foo: bar\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_unknown_nested_key_fails_fast(tmp_path: Path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "agent_id: x\nmodel:\n  primary: gemini-2.5-pro\n  surprise: nope\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_routing_default_rejects_bad_value(tmp_path: Path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "agent_id: x\nrouting:\n  last_resort_default: shrug\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_load_missing_file_raises_file_not_found():
    from app.agents.runtime.operations_config import OperationsConfig

    with pytest.raises(FileNotFoundError):
        OperationsConfig.load(Path("/nonexistent/operations.yaml"))


def test_malformed_yaml_raises_clear_value_error(tmp_path: Path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    # Unclosed flow mapping — guaranteed YAML parse error.
    bad.write_text("agent_id: x\nmodel: {primary: gemini\n", encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        OperationsConfig.load(bad)

    # Surface should be a ValueError with a clear message, not a raw YAMLError.
    msg = str(excinfo.value)
    assert "not valid YAML" in msg
    assert str(bad) in msg


def test_top_level_must_be_mapping(tmp_path: Path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text("- agent_id: x\n", encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        OperationsConfig.load(bad)

    assert "mapping" in str(excinfo.value)


def test_model_dump_roundtrip_is_identity():
    from app.agents.runtime.operations_config import OperationsConfig

    cfg = OperationsConfig.load(FIX / "operations_financial.yaml")
    dumped = cfg.model_dump()
    revived = OperationsConfig.model_validate(dumped)

    assert revived == cfg
    assert revived.model_dump() == dumped


def test_minimal_roundtrip_is_identity():
    from app.agents.runtime.operations_config import OperationsConfig

    cfg = OperationsConfig.load(FIX / "operations_minimal.yaml")
    dumped = cfg.model_dump()
    revived = OperationsConfig.model_validate(dumped)

    assert revived == cfg
    assert revived.model_dump() == dumped


def test_empty_yaml_file_raises_validation_error(tmp_path: Path):
    """An empty YAML file is treated as `{}` — missing agent_id must error."""
    from app.agents.runtime.operations_config import OperationsConfig

    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError):
        OperationsConfig.load(empty)


def test_load_accepts_string_path(tmp_path: Path):
    """load() accepts both Path and str — useful for env-var driven config."""
    from app.agents.runtime.operations_config import OperationsConfig

    p = tmp_path / "ok.yaml"
    p.write_text("agent_id: stringpath\n", encoding="utf-8")

    cfg = OperationsConfig.load(str(p))
    assert cfg.agent_id == "stringpath"
