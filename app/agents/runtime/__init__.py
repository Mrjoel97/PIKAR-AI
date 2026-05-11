# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Runtime support package for PikarBaseAgent.

Re-exports the small set of names that Section B/C/D will reach for first:
  - OperationsConfig: loaded by PikarBaseAgent.__init__
  - lifecycle: callback factories wired by PikarBaseAgent

Heavy submodules (types, research_gate, persona_gate, etc.) are NOT
imported here — consumers reach for them with explicit
``from app.agents.runtime.types import TaskContract``.
"""

from app.agents.runtime import lifecycle as lifecycle
from app.agents.runtime.operations_config import OperationsConfig as OperationsConfig

__all__ = ["OperationsConfig", "lifecycle"]
