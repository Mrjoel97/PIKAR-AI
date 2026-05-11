# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools manifest — name-string -> callable resolution for an agent.

Section A scope (Task 19): a thin shim. ``ToolsManifest.resolve()`` returns
an empty list. Section E (the financial pilot, Tasks 75+) replaces the body
with real lookup against ``app.agents.tools`` so agents can declare their
tool surface as YAML rather than Python imports.

The :class:`ToolsManifest` dataclass is the canonical concrete carrier; the
:class:`~app.agents.base_agent.PikarBaseAgent` constructor accepts any
object whose ``.resolve()`` returns a list of callables (duck-typed) so
tests and alternative manifest sources can plug in without subclassing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolsManifest:
    """Declarative manifest of the tool callables an agent may use.

    Section A: only carries the ``tool_ids`` list and returns an empty
    callable list from :meth:`resolve`. Section E will swap the body to
    consult ``app.agents.tools`` (and the per-domain tool factories) so
    YAML-declared agents pick up their real surface.
    """

    tool_ids: list[str] = field(default_factory=list)

    def resolve(self) -> list[Any]:
        """Resolve ``tool_ids`` to concrete tool callables.

        Section A stub: returns an empty list. The financial pilot
        (Section E) wires this up to the real tool registry; until then,
        any agent built via this manifest runs with no tools, which is
        acceptable because Section A only exercises the constructor path.
        """
        return []


__all__ = ["ToolsManifest"]
