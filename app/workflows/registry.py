"""Workflow Registry.

Central registry that maps workflow names to their factory functions.
Factory functions are imported from domain-specific workflow modules
(initiative, marketing, sales, etc.) and registered at app startup
via ``bootstrap_registry()``.
"""

import logging
from typing import Any, Callable, Optional, Dict, List

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """Central registry for workflow factory function lookup and management."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories: Dict[str, Callable] = {}
            cls._instance._metadata: Dict[str, Dict[str, Any]] = {}
            cls._instance._bootstrapped = False
        return cls._instance

    def register(self, name: str, factory: Callable, metadata: Optional[Dict[str, Any]] = None):
        """Register a workflow factory."""
        self._factories[name] = factory
        if metadata:
            self._metadata[name] = metadata

    def get(self, name: str) -> Optional[Any]:
        """Create a new workflow instance by name."""
        self._ensure_bootstrapped()
        factory = self._factories.get(name)
        if factory:
            return factory()
        return None

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Get metadata for a registered workflow."""
        self._ensure_bootstrapped()
        return self._metadata.get(name, {})

    def list_all(self) -> List[str]:
        self._ensure_bootstrapped()
        return list(self._factories.keys())

    def list_by_persona(self, persona: str) -> List[str]:
        """List workflows recommended for a specific persona."""
        self._ensure_bootstrapped()
        persona = persona.lower()
        matching = []
        for name, meta in self._metadata.items():
            allowed = meta.get("personas", [])
            if "all" in allowed or persona in allowed:
                matching.append(name)
        return matching

    def list_by_category(self, category: str) -> List[str]:
        self._ensure_bootstrapped()
        return [
            name for name, meta in self._metadata.items()
            if meta.get("category") == category
        ]

    def _ensure_bootstrapped(self):
        """Lazy-bootstrap on first access if not already done."""
        if not self._bootstrapped:
            bootstrap_registry()


# Simple singleton accessor
_registry = WorkflowRegistry()


def get_workflow_registry():
    return _registry


# Aliases expected by __init__.py and other modules
workflow_registry = _registry


def get_workflow(name: str):
    """Get a workflow by name."""
    return _registry.get(name)


def list_workflows():
    """List all registered workflows."""
    return _registry.list_all()


def get_workflow_factory(name: str):
    """Get the factory function for a workflow."""
    _registry._ensure_bootstrapped()
    return _registry._factories.get(name)


def bootstrap_registry() -> None:
    """Import all workflow factory modules and register their factories.

    This is called lazily on first registry access, or can be called
    explicitly at app startup for eager initialization.

    Each workflow module exports a ``*_WORKFLOW_FACTORIES`` dict mapping
    display names to factory callables. We register every entry plus
    metadata derived from the module's domain.
    """
    if _registry._bootstrapped:
        return
    _registry._bootstrapped = True

    _FACTORY_MODULES = [
        ("app.workflows.initiative", "INITIATIVE_WORKFLOW_FACTORIES", "initiative", ["all"]),
        ("app.workflows.compliance", "COMPLIANCE_WORKFLOW_FACTORIES", "compliance", ["sme", "enterprise"]),
        ("app.workflows.documentation", "DOCUMENTATION_WORKFLOW_FACTORIES", "documentation", ["all"]),
        ("app.workflows.evaluation", "EVALUATION_WORKFLOW_FACTORIES", "evaluation", ["sme", "enterprise"]),
        ("app.workflows.financial", "FINANCIAL_WORKFLOW_FACTORIES", "financial", ["all"]),
        ("app.workflows.goals", "GOALS_WORKFLOW_FACTORIES", "goals", ["all"]),
        ("app.workflows.hr", "HR_WORKFLOW_FACTORIES", "hr", ["sme", "enterprise"]),
        ("app.workflows.knowledge", "KNOWLEDGE_WORKFLOW_FACTORIES", "knowledge", ["all"]),
        ("app.workflows.marketing", "MARKETING_WORKFLOW_FACTORIES", "marketing", ["all"]),
        ("app.workflows.product", "PRODUCT_WORKFLOW_FACTORIES", "product", ["startup", "sme", "enterprise"]),
        ("app.workflows.sales", "SALES_WORKFLOW_FACTORIES", "sales", ["all"]),
    ]

    total = 0
    for module_path, attr_name, category, personas in _FACTORY_MODULES:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            factories: Dict[str, Callable] = getattr(mod, attr_name, {})
            for name, factory in factories.items():
                _registry.register(
                    name,
                    factory,
                    metadata={
                        "category": category,
                        "personas": personas,
                        "module": module_path,
                    },
                )
                total += 1
        except Exception as exc:
            logger.warning("Failed to load workflow factories from %s: %s", module_path, exc)

    logger.info("WorkflowRegistry bootstrapped: %d factories from %d modules", total, len(_FACTORY_MODULES))
