# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Pikar agent runtime — gates, audit, persona, router, lifecycle.

Section A defines ``types`` and ``operations_config``. Section C wires in the
gate modules below. Other sections add lifecycle/handoff/publication on top.

The heavy ``types`` submodule is intentionally NOT imported at the package
level — consumers reach for it with explicit
``from app.agents.runtime.types import TaskContract`` so agent start-up stays
cheap. The lazy-load invariant is asserted by
``tests/unit/agents/runtime/test_package_init.py::test_runtime_package_is_a_namespace_for_submodules``.
"""

from app.agents.runtime import lifecycle as lifecycle
from app.agents.runtime.audit import (
    attach_audit_summary_to_evidence,
    audit_against_contract,
    persist_audit_report,
)
from app.agents.runtime.operations_config import OperationsConfig as OperationsConfig
from app.agents.runtime.persona_gate import (
    apply_prompt_fragments,
    check_action_threshold,
    check_tool_allowed,
    load_persona_policy,
    record_violation,
)
from app.agents.runtime.research_gate import (
    RESEARCH_TOOL_IDS,
    check_coverage,
    close_gate,
    is_open,
    open_gate,
    record_tool_result,
)
from app.agents.runtime.task_router import (
    DIRECT_LENGTH_THRESHOLD,
    DIRECT_VERBS,
    INITIATIVE_VERBS,
    classify,
)

__all__ = [
    "DIRECT_LENGTH_THRESHOLD",
    "DIRECT_VERBS",
    "INITIATIVE_VERBS",
    "RESEARCH_TOOL_IDS",
    "OperationsConfig",
    "apply_prompt_fragments",
    "attach_audit_summary_to_evidence",
    "audit_against_contract",
    "check_action_threshold",
    "check_coverage",
    "check_tool_allowed",
    "classify",
    "close_gate",
    "is_open",
    "lifecycle",
    "load_persona_policy",
    "open_gate",
    "persist_audit_report",
    "record_tool_result",
    "record_violation",
]
