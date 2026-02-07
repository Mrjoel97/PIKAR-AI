"""Base utilities for agent tools."""
from functools import wraps
from typing import Callable, Any


def agent_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark a function as an agent tool.
    
    This decorator wraps tool functions for use by the ADK agent system.
    It preserves the function signature and docstring for LLM introspection.
    
    Args:
        func: The tool function to wrap.
        
    Returns:
        The wrapped function with tool metadata.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    
    # Mark as agent tool for discovery
    wrapper._is_agent_tool = True
    return wrapper
