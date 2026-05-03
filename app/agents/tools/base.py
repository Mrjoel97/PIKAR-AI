# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Base utilities for agent tools."""

import asyncio
import enum
import inspect
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, get_args, get_origin, get_type_hints

logger = logging.getLogger(__name__)


def _contains_dict_type(hint: Any) -> bool:
    """Check if a type hint contains Dict at any nesting level.

    Gemini API rejects schemas with 'additionalProperties' which Python's
    Dict[str, Any] / Dict[str, str] type hints generate. This helper
    detects such types so we can convert them to 'str' (JSON string) in
    the schema while transparently parsing them back for the function.
    """
    # Bare dict class
    if hint is dict:
        return True
    origin = get_origin(hint)
    # typing.Dict → origin is dict
    if origin is dict:
        return True
    # Recurse into type args (e.g., List[Dict[str, Any]], Optional[Dict])
    args = get_args(hint)
    if args:
        return any(_contains_dict_type(a) for a in args if a is not type(None))
    return False


def _is_numeric_enum_type(hint: Any) -> bool:
    """Return True when a hint is an Enum backed by a non-string primitive.

    Vertex Gemini function declarations reject numeric enum values in response
    schemas. When a tool returns something like ``IntEnum``, we expose it to the
    model as a plain string instead.
    """
    try:
        return inspect.isclass(hint) and issubclass(hint, enum.Enum) and not issubclass(
            hint, str
        )
    except TypeError:
        return False


def _parse_dict_kwargs(dict_params: set[str], kwargs: dict, func_name: str) -> None:
    """Parse JSON strings back to Python objects for Dict-typed params (in-place)."""
    for key in list(kwargs.keys()):
        if key in dict_params and isinstance(kwargs[key], str):
            try:
                kwargs[key] = json.loads(kwargs[key])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse JSON for param '{key}' in {func_name}")


def _apply_schema_overrides(
    wrapper: Callable,
    func: Callable,
    dict_params: set[str],
    modified_hints: dict,
    numeric_enum_return: bool,
) -> None:
    """Override annotations and __signature__ so ADK generates Gemini-compatible schemas."""
    wrapper.__annotations__ = modified_hints
    orig_sig = inspect.signature(func)
    new_params = []
    for param_name, param in orig_sig.parameters.items():
        if param_name in dict_params:
            new_params.append(param.replace(annotation=str))
        else:
            new_params.append(param)
    return_annotation = str if numeric_enum_return else orig_sig.return_annotation
    wrapper.__signature__ = orig_sig.replace(
        parameters=new_params,
        return_annotation=return_annotation,
    )
    logger.debug(
        "agent_tool: applied schema overrides to %s (dict_params=%s, numeric_enum_return=%s)",
        func.__name__,
        dict_params,
        numeric_enum_return,
    )


def agent_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark a function as an agent tool.

    This decorator wraps tool functions for use by the ADK agent system.
    It preserves the function signature and docstring for LLM introspection.

    **Gemini Compatibility**: Automatically converts parameters typed as
    List[Dict[...]] or Dict[...] to ``str`` in the schema (the Gemini API
    rejects ``additionalProperties``). When the LLM passes a JSON string,
    the decorator transparently parses it back to a Python object before
    calling the original function.

    Handles both sync and async tool functions.

    Args:
        func: The tool function to wrap.

    Returns:
        The wrapped function with tool metadata.
    """
    # Already wrapped — skip
    if getattr(func, "_is_agent_tool", False):
        return func

    # Resolve postponed annotations (`from __future__ import annotations`) so
    # schema sanitization sees the real Python types instead of raw strings.
    try:
        original_hints: dict = get_type_hints(func)
    except Exception:
        original_hints = getattr(func, "__annotations__", {}).copy()
    dict_params: set[str] = set()
    modified_hints: dict = {}
    numeric_enum_return = False

    for name, hint in original_hints.items():
        if name == "return":
            if _is_numeric_enum_type(hint):
                numeric_enum_return = True
                modified_hints[name] = str
            else:
                modified_hints[name] = hint
            continue
        if _contains_dict_type(hint):
            dict_params.add(name)
            modified_hints[name] = str
        else:
            modified_hints[name] = hint

    # Choose sync or async wrapper to preserve coroutine-function detection
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if dict_params:
                _parse_dict_kwargs(dict_params, kwargs, func.__name__)
            result = await func(*args, **kwargs)
            if numeric_enum_return and isinstance(result, enum.Enum):
                return result.name.lower()
            return result
    else:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if dict_params:
                _parse_dict_kwargs(dict_params, kwargs, func.__name__)
            result = func(*args, **kwargs)
            if numeric_enum_return and isinstance(result, enum.Enum):
                return result.name.lower()
            return result

    # Override annotations AND __signature__ so ADK generates Gemini-compatible schemas.
    if dict_params or numeric_enum_return:
        _apply_schema_overrides(
            wrapper,
            func,
            dict_params,
            modified_hints,
            numeric_enum_return,
        )

    # Mark as agent tool for discovery
    wrapper._is_agent_tool = True
    return wrapper


def sanitize_tools(tools: list[Callable]) -> list[Callable]:
    """Apply agent_tool to every function in *tools* that has Dict params.

    Called centrally in the tool registry so individual tool modules
    don't need to import or apply the decorator themselves.
    """
    return [agent_tool(t) for t in tools]
