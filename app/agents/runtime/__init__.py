# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Runtime support package for PikarBaseAgent.

Submodules (loaded lazily by callers):
  - types: shared Pydantic / dataclass contracts.
  - operations_config: operations.yaml loader + validator.
  - lifecycle: ADK before/after callbacks (stubs in Section A; bodies in Section B).
  - research_gate, audit, persona_gate, task_router, ...

Importing this package must NOT pull heavy submodules; downstream code does
`from app.agents.runtime.types import TaskContract` so each consumer pays
only for what it needs.
"""
