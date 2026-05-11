"""Path-isolation shim for the runtime integration tests.

A leftover editable install (``_editable_impl_pikar_ai.pth``) points
``site-packages`` at ``.claude/worktrees/live-workflow-view`` on this
developer workstation, which can cause ``app.agents.runtime`` to resolve
to a stale copy of the runtime package missing newer submodules
(``publication``, ``step_runtime``, ...).

We prepend the *current* project root to ``sys.path`` so the local copy
always wins. See ``MEMORY/project_branch_pollution_2026_05_09.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/integration/agents/runtime/conftest.py  ->  project root is 4 up.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
elif sys.path[0] != str(_PROJECT_ROOT):
    sys.path.remove(str(_PROJECT_ROOT))
    sys.path.insert(0, str(_PROJECT_ROOT))

# Eagerly evict any prior ``app`` namespace that came from the worktree
# copy of the package — its ``__init__.py`` is missing the submodules
# this test imports.
for _modname in list(sys.modules):
    if _modname == "app" or _modname.startswith("app."):
        _mod = sys.modules[_modname]
        _file = getattr(_mod, "__file__", None) or ""
        if ".claude\\worktrees" in _file or ".claude/worktrees" in _file:
            del sys.modules[_modname]
