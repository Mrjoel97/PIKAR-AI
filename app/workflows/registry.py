"""Workflow Registry."""

from typing import Any, Callable, Optional, Dict, List

class WorkflowRegistry:
    """Central registry for workflow factory function lookup and management."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories = {}
            cls._instance._metadata = {}
        return cls._instance

    def register(self, name: str, factory: Callable, metadata: Optional[Dict[str, Any]] = None):
        """Register a workflow factory."""
        self._factories[name] = factory
        if metadata:
            self._metadata[name] = metadata

    def get(self, name: str) -> Optional[Any]:
        """Create a new workflow instance."""
        factory = self._factories.get(name)
        if factory:
            return factory()
        return None

    def list_all(self) -> List[str]:
        return list(self._factories.keys())

    def list_by_persona(self, persona: str) -> List[str]:
        """List workflows recommended for a specific persona."""
        persona = persona.lower()
        matching = []
        for name, meta in self._metadata.items():
            allowed = meta.get("personas", [])
            if "all" in allowed or persona in allowed:
                matching.append(name)
        return matching

    def list_by_category(self, category: str) -> List[str]:
        return [
            name for name, meta in self._metadata.items()
            if meta.get("category") == category
        ]

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
    return _registry._factories.get(name)
