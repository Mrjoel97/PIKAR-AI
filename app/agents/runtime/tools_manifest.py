# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools manifest -- name-string -> callable resolution for an agent.

Section A shipped this as a stub returning ``[]``. Section E (the financial
pilot, Task 108) replaces ``resolve()`` with a real lookup that walks each
declared ``tool_id`` against, in order:

1. The agent's own ``app.agents.<domain>.tools`` module (when supplied via
   :attr:`ToolsManifest.local_tools_module`).
2. The shared ``app.agents.tools.<id>`` module — looking either for an
   exported ``<UPPER>_TOOLS`` list (the codebase convention), a function
   whose name matches the id, or the module itself wrapped in a deferred
   callable.

Every declared id resolves to exactly one callable so the
:class:`~app.agents.base_agent.PikarBaseAgent` constructor can pass the
result directly into ADK's ``tools=`` kwarg. When multiple callables live
behind one id (a shared tool pack), :class:`_ToolPack` wraps the list so
the id is preserved AND the underlying callables stay reachable via
``pack.tools`` for downstream introspection.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool-pack wrapper
# ---------------------------------------------------------------------------


@dataclass
class _ToolPack:
    """Callable wrapper around a shared tool module's exported callable list.

    The ADK ``tools=`` kwarg accepts a flat list of callables. Shared tool
    packs (``INVOICE_TOOLS``, ``STRIPE_TOOLS``, etc.) export multiple
    callables under a single module name; this wrapper keeps the manifest
    1-callable-per-id while still letting downstream code reach into the
    underlying list via ``pack.tools``.

    Calling the pack itself is intentionally a no-op (returns the tools
    list) -- the ADK runtime never invokes a manifest entry directly; it
    only walks the list. Tests assert ``callable(entry)`` which is what
    this dataclass guarantees.
    """

    id: str
    tools: list[Callable[..., Any]]

    def __call__(self, *args: Any, **kwargs: Any) -> list[Callable[..., Any]]:
        """Return the underlying tool list (kept so ``callable(pack)`` is True)."""
        return list(self.tools)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def _try_local(module_path: str | None, tool_id: str) -> Callable[..., Any] | None:
    """Try to resolve ``tool_id`` against ``module_path`` (the agent's own tools).

    Returns the attribute if it is callable, ``None`` otherwise. Import
    failures degrade to ``None`` so a stale or missing per-agent module
    does not break the manifest -- the shared lookup is tried next.
    """
    if not module_path:
        return None
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001 -- best effort
        logger.debug("local tools module %s import failed: %s", module_path, exc)
        return None
    attr = getattr(module, tool_id, None)
    return attr if callable(attr) else None


# Known shared tool packs: maps the canonical id used in operations to the
# (module, attr_name) tuple. ``attr_name`` may be a ``*_TOOLS`` list (most
# packs follow this convention) OR a single function name (a handful of
# single-function modules whose function name differs from the module
# name, e.g. ``knowledge.search_knowledge``).
_TOOL_PACK_ALIASES: dict[str, tuple[str, str]] = {
    "invoicing": ("app.agents.tools.invoicing", "INVOICE_TOOLS"),
    "deep_research": ("app.agents.tools.deep_research", "DEEP_RESEARCH_TOOLS"),
    "quick_research": ("app.agents.tools.quick_research", "QUICK_RESEARCH_TOOLS"),
    "approval_tool": ("app.agents.tools.approval_tool", "APPROVAL_TOOLS"),
    "graph_tools": ("app.agents.tools.graph_tools", "GRAPH_TOOLS"),
    "ui_widgets": ("app.agents.tools.ui_widgets", "UI_WIDGET_TOOLS"),
    "context_memory": ("app.agents.tools.context_memory", "CONTEXT_MEMORY_TOOLS"),
    "document_gen": ("app.agents.tools.document_gen", "DOCUMENT_GEN_TOOLS"),
    "stripe_tools": ("app.agents.tools.stripe_tools", "STRIPE_TOOLS"),
    "shopify_tools": ("app.agents.tools.shopify_tools", "SHOPIFY_TOOLS"),
    "report_scheduling": (
        "app.agents.tools.report_scheduling",
        "REPORT_SCHEDULING_TOOLS",
    ),
    # Single-function modules whose exported callable name differs from
    # the module filename. The resolver detects callability and returns
    # the function directly (skipping the _ToolPack wrap).
    "knowledge": ("app.agents.tools.knowledge", "search_knowledge"),
    "system_knowledge": (
        "app.agents.tools.system_knowledge",
        "search_system_knowledge",
    ),
}


def _try_shared(tool_id: str) -> Callable[..., Any] | None:
    """Resolve ``tool_id`` against the ``app.agents.tools`` package.

    Resolution order, all best-effort:

    1. Known alias from :data:`_TOOL_PACK_ALIASES` (handles the small set of
       historic naming mismatches).
    2. Module ``app.agents.tools.<tool_id>``: look for the function whose
       name matches ``tool_id`` (single-function modules), then for an
       exported ``<TOOL_ID.upper()>_TOOLS`` list, then for any other
       ``*_TOOLS`` list at module level.
    3. Returns ``None`` when no resolution succeeds; the manifest then
       wraps the absence with a no-op callable so the 1-to-1 contract is
       preserved while still surfacing the missing tool in logs.
    """
    if tool_id in _TOOL_PACK_ALIASES:
        module_path, attr_name = _TOOL_PACK_ALIASES[tool_id]
        try:
            module = importlib.import_module(module_path)
            target = getattr(module, attr_name, None)
            if isinstance(target, list) and target:
                return _ToolPack(id=tool_id, tools=list(target))
            if callable(target):
                return target
        except Exception as exc:  # noqa: BLE001
            logger.debug("shared pack %s import failed: %s", module_path, exc)
        # Alias known but import failed: fall through to generic lookup so
        # a renamed module still has a chance to resolve.

    module_path = f"app.agents.tools.{tool_id}"
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001 -- best effort
        logger.debug("shared module %s import failed: %s", module_path, exc)
        return None

    # Single function whose name matches the id.
    direct = getattr(module, tool_id, None)
    if callable(direct):
        return direct

    # Conventional ``<TOOL_ID.upper()>_TOOLS`` export.
    upper_attr = f"{tool_id.upper()}_TOOLS"
    tools = getattr(module, upper_attr, None)
    if isinstance(tools, list) and tools:
        return _ToolPack(id=tool_id, tools=list(tools))

    # Last-resort scan for any ``*_TOOLS`` list at module level.
    for name in dir(module):
        if name.endswith("_TOOLS"):
            candidate = getattr(module, name, None)
            if isinstance(candidate, list) and candidate:
                return _ToolPack(id=tool_id, tools=list(candidate))

    return None


def _missing_tool(tool_id: str) -> Callable[..., Any]:
    """Build a no-op callable for a tool id that did not resolve.

    Kept distinct from the real resolutions so a downstream caller (or a
    test asserting tools wire up correctly) can detect the placeholder
    via ``getattr(fn, "missing_tool_id", None)``.
    """

    def _placeholder(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "success": False,
            "error": f"tool '{tool_id}' is declared in the manifest but no "
            f"implementation could be resolved",
        }

    _placeholder.missing_tool_id = tool_id  # type: ignore[attr-defined]
    _placeholder.__name__ = f"missing_{tool_id}"
    return _placeholder


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolsManifest:
    """Declarative manifest of the tool callables an agent may use.

    Each entry in :attr:`tool_ids` resolves to exactly one callable via
    :meth:`resolve` (either a direct function reference or a
    :class:`_ToolPack` wrapping a shared tool-module's exported list).
    Setting :attr:`local_tools_module` lets the resolver consult the
    owning agent's own ``tools.py`` for local-callable ids before falling
    through to the shared registry under ``app.agents.tools``.
    """

    tool_ids: list[str] = field(default_factory=list)
    local_tools_module: str | None = None

    def resolve(self) -> list[Callable[..., Any]]:
        """Resolve every declared id to a single callable.

        Resolution order per id:

        1. :attr:`local_tools_module` (when set) — matches local async
           callables defined by the agent's own ``tools.py`` (e.g.
           ``get_revenue_stats`` lives in
           ``app.agents.financial.tools``).
        2. ``app.agents.tools.<id>`` — shared tool packs and single-function
           modules; see :func:`_try_shared`.
        3. A placeholder no-op callable (Section E intentional fallback)
           so the 1-to-1 contract with :attr:`tool_ids` is preserved
           even when a declared id is currently unresolved.
        """
        resolved: list[Callable[..., Any]] = []
        for tool_id in self.tool_ids:
            local = _try_local(self.local_tools_module, tool_id)
            if local is not None:
                resolved.append(local)
                continue
            shared = _try_shared(tool_id)
            if shared is not None:
                resolved.append(shared)
                continue
            logger.warning(
                "ToolsManifest could not resolve tool id %r -- "
                "wrapping in placeholder",
                tool_id,
            )
            resolved.append(_missing_tool(tool_id))
        return resolved


__all__ = ["ToolsManifest"]
