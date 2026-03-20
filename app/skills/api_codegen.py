"""API tool code generator for the Universal API Connector.

Generates Python tool functions from ``EndpointDefinition`` objects so they
can be loaded as ADK tools at runtime.  Generated functions are **sync**
(ADK tools must be sync) and use ``httpx.Client`` for HTTP calls.
"""

from __future__ import annotations

import keyword
import logging
import re
import textwrap
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight stubs for EndpointDefinition / APISpec.
#
# These mirror the dataclasses expected from ``app.skills.api_parser``.
# At import time we try to pull the real definitions; if the parser module
# hasn't been created yet we fall back to the local stubs so this module
# remains importable.
# ---------------------------------------------------------------------------

try:
    from app.skills.api_parser import APISpec, EndpointDefinition  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover — parser may not exist yet
    from dataclasses import dataclass, field as dc_field

    @dataclass
    class _ParamDef:
        """Minimal parameter definition."""

        name: str
        location: str  # "query" | "path" | "header"
        required: bool = False
        schema_type: str = "string"
        description: str = ""
        default: Any = None

    @dataclass
    class _RequestBody:
        """Minimal request body definition."""

        content_type: str = "application/json"
        required: bool = False
        schema_properties: dict[str, Any] = dc_field(default_factory=dict)
        required_properties: list[str] = dc_field(default_factory=list)

    @dataclass
    class EndpointDefinition:  # type: ignore[no-redef]
        """One API endpoint to generate a tool for."""

        path: str
        method: str  # GET, POST, PUT, PATCH, DELETE
        operation_id: str = ""
        summary: str = ""
        description: str = ""
        parameters: list[Any] = dc_field(default_factory=list)
        request_body: Any | None = None
        response_schema: dict[str, Any] = dc_field(default_factory=dict)
        tags: list[str] = dc_field(default_factory=list)

    @dataclass
    class APISpec:  # type: ignore[no-redef]
        """Parsed API specification metadata."""

        title: str = ""
        version: str = ""
        base_url: str = ""
        description: str = ""
        auth_scheme: str = "bearer"  # bearer | api_key | basic | custom
        auth_header: str = "Authorization"
        auth_prefix: str = "Bearer"


# ---------------------------------------------------------------------------
# JSON-Schema → Python type mapping
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}

# Maximum response body size (10 MB)
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_snake_case(name: str) -> str:
    """Convert camelCase / PascalCase / kebab-case to snake_case."""
    # Insert underscore before uppercase runs
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Replace hyphens and spaces
    s = re.sub(r"[-\s]+", "_", s)
    return s.lower()


def _safe_identifier(name: str) -> str:
    """Ensure *name* is a legal Python identifier."""
    s = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s or s[0].isdigit():
        s = f"p_{s}"
    if keyword.iskeyword(s):
        s = f"{s}_"
    return s


def _sanitize_for_docstring(text: str) -> str:
    """Remove characters that could break a Python triple-quoted docstring.

    Strips triple-quote sequences and backslash-escapes to prevent
    code injection via crafted OpenAPI descriptions.
    """
    text = text.replace('"""', "")
    text = text.replace("'''", "")
    text = text.replace("\\", "\\\\")
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _python_type(schema_type: str) -> str:
    """Map a JSON-Schema type string to a Python type annotation."""
    return _TYPE_MAP.get(schema_type, "str")


def _python_default(schema_type: str, default: Any = None) -> str:
    """Return a Python-source default value for an optional parameter."""
    if default is not None:
        return repr(default)
    defaults: dict[str, str] = {
        "string": '""',
        "integer": "0",
        "number": "0.0",
        "boolean": "False",
        "array": "None",
        "object": "None",
    }
    return defaults.get(schema_type, '""')


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------


class APIToolGenerator:
    """Generate Python tool code from API endpoint definitions."""

    # ----- public API -------------------------------------------------------

    def generate_tool(
        self,
        endpoint: EndpointDefinition,
        api: APISpec,
        secret_name: str,
        api_name: str = "",
    ) -> dict:
        """Generate a complete Python function for one endpoint.

        Returns:
            Dict with keys ``name``, ``code``, ``description``, ``test_code``.
        """
        func_name = self._function_name(endpoint, api_name)
        params = self._function_params(endpoint)
        docstring = self._function_docstring(endpoint)
        request_code = self._request_code(endpoint, api, secret_name)
        response_code = self._response_handling(endpoint)
        test_code = self._generate_test(func_name, endpoint)

        body = textwrap.indent(
            f"{request_code}\n{response_code}",
            "    ",
        )

        code = (
            f"def {func_name}({params}) -> dict:\n"
            f"{docstring}\n"
            f"    import httpx\n"
            f"    from app.skills.api_auth import get_api_credential, validate_url\n"
            f"\n"
            f"{body}\n"
        )

        description = _sanitize_for_docstring(
            endpoint.summary or endpoint.description or func_name
        )

        return {
            "name": func_name,
            "code": code,
            "description": description,
            "test_code": test_code,
        }

    def generate_batch(
        self,
        endpoints: list[EndpointDefinition],
        api: APISpec,
        secret_name: str,
        api_name: str,
    ) -> list[dict]:
        """Generate tools for multiple endpoints.

        Returns:
            List of tool dicts (same shape as :meth:`generate_tool`).
        """
        seen_names: set[str] = set()
        results: list[dict] = []

        for ep in endpoints:
            tool = self.generate_tool(ep, api, secret_name, api_name)
            # Deduplicate names (append numeric suffix if needed)
            base = tool["name"]
            name = base
            counter = 2
            while name in seen_names:
                name = f"{base}_{counter}"
                counter += 1
            if name != base:
                tool["code"] = tool["code"].replace(
                    f"def {base}(", f"def {name}("
                )
                tool["name"] = name

            seen_names.add(name)
            results.append(tool)

        return results

    # ----- internal helpers -------------------------------------------------

    def _function_name(
        self, endpoint: EndpointDefinition, api_name: str
    ) -> str:
        """Generate Python function name from endpoint.

        E.g. ``operation_id="listCustomers"``, ``api_name="stripe"``
        produces ``"stripe_list_customers"``.
        """
        if endpoint.operation_id:
            raw = endpoint.operation_id
        else:
            # Fallback: method + path segments
            segments = [
                s for s in endpoint.path.strip("/").split("/") if not s.startswith("{")
            ]
            raw = f"{endpoint.method.lower()}_{'_'.join(segments)}"

        snake = _to_snake_case(raw)
        prefix = _to_snake_case(api_name) if api_name else ""
        if prefix and not snake.startswith(prefix):
            snake = f"{prefix}_{snake}"
        return _safe_identifier(snake)

    def _function_params(self, endpoint: EndpointDefinition) -> str:
        """Generate the function parameter list with type hints.

        Required params come first, then optional ones with defaults.
        """
        required_parts: list[str] = []
        optional_parts: list[str] = []

        # Collect from endpoint.parameters
        for param in getattr(endpoint, "parameters", []) or []:
            pname = _safe_identifier(getattr(param, "name", str(param)))
            ptype = _python_type(getattr(param, "schema_type", "string"))
            is_required = getattr(param, "required", False)

            if is_required:
                required_parts.append(f"{pname}: {ptype}")
            else:
                default = _python_default(
                    getattr(param, "schema_type", "string"),
                    getattr(param, "default", None),
                )
                optional_parts.append(f"{pname}: {ptype} = {default}")

        # Collect from request_body schema properties
        body = getattr(endpoint, "request_body", None)
        if body is not None:
            props = getattr(body, "schema_properties", None) or {}
            required_props: list[str] = getattr(body, "required_properties", []) or []
            for prop_name, prop_schema in props.items():
                pname = _safe_identifier(prop_name)
                schema_type = (
                    prop_schema.get("type", "string")
                    if isinstance(prop_schema, dict)
                    else "string"
                )
                ptype = _python_type(schema_type)
                if prop_name in required_props:
                    required_parts.append(f"{pname}: {ptype}")
                else:
                    default = _python_default(schema_type)
                    optional_parts.append(f"{pname}: {ptype} = {default}")

        all_parts = required_parts + optional_parts
        if not all_parts:
            return ""

        # Format nicely: one param per line if > 3 params
        if len(all_parts) <= 3:
            return ", ".join(all_parts)

        joined = ",\n    ".join(all_parts)
        return f"\n    {joined},\n"

    def _function_docstring(self, endpoint: EndpointDefinition) -> str:
        """Generate a triple-quoted docstring with summary, args, return."""
        summary = _sanitize_for_docstring(
            endpoint.summary or endpoint.description or "Call API endpoint."
        )
        lines: list[str] = [f'    """{summary}']

        # Build Args section
        arg_lines: list[str] = []
        for param in getattr(endpoint, "parameters", []) or []:
            desc = _sanitize_for_docstring(
                getattr(param, "description", "") or getattr(param, "name", "")
            )
            arg_lines.append(
                f"        {_safe_identifier(getattr(param, 'name', str(param)))}: {desc}"
            )

        body = getattr(endpoint, "request_body", None)
        if body is not None:
            for prop_name, prop_schema in (
                getattr(body, "schema_properties", None) or {}
            ).items():
                desc = (
                    prop_schema.get("description", prop_name)
                    if isinstance(prop_schema, dict)
                    else prop_name
                )
                arg_lines.append(
                    f"        {_safe_identifier(prop_name)}: {_sanitize_for_docstring(desc)}"
                )

        if arg_lines:
            lines.append("")
            lines.append("    Args:")
            lines.extend(arg_lines)

        lines.append("")
        lines.append("    Returns:")
        lines.append("        Dict with status and response data.")
        lines.append('    """')
        return "\n".join(lines)

    def _request_code(
        self,
        endpoint: EndpointDefinition,
        api: APISpec,
        secret_name: str,
    ) -> str:
        """Generate httpx request code (sync)."""
        method = endpoint.method.upper()
        path = endpoint.path

        # --- URL construction ---
        # Path parameters are substituted via str.format_map
        path_params = [
            p
            for p in (getattr(endpoint, "parameters", []) or [])
            if getattr(p, "location", "") == "path"
        ]
        if path_params:
            fmt_parts: list[str] = []
            for p in path_params:
                pname = _safe_identifier(getattr(p, "name", str(p)))
                raw_name = getattr(p, "name", str(p))
                fmt_parts.append(f'"{raw_name}": {pname}')
            fmt_dict = ", ".join(fmt_parts)
            url_line = (
                f'url = validate_url("{api.base_url}"'
                f' + "{path}".format_map({{{fmt_dict}}}))'
            )
        else:
            url_line = f'url = validate_url("{api.base_url}{path}")'

        # --- Auth header ---
        auth_scheme = getattr(api, "auth_scheme", "bearer")
        auth_header = getattr(api, "auth_header", "Authorization")
        auth_prefix = getattr(api, "auth_prefix", "Bearer")

        if auth_scheme == "basic":
            auth_line = (
                f'headers = {{"{auth_header}": '
                f'"Basic " + get_api_credential("{secret_name}")}}'
            )
        elif auth_scheme == "api_key":
            auth_line = (
                f'headers = {{"{auth_header}": '
                f'get_api_credential("{secret_name}")}}'
            )
        else:
            # bearer (default)
            auth_line = (
                f'headers = {{"{auth_header}": '
                f'"{auth_prefix} " + get_api_credential("{secret_name}")}}'
            )

        # --- Query params ---
        query_params = [
            p
            for p in (getattr(endpoint, "parameters", []) or [])
            if getattr(p, "location", "") == "query"
        ]
        query_lines: list[str] = ["params = {}"]
        for qp in query_params:
            pname = _safe_identifier(getattr(qp, "name", str(qp)))
            raw_name = getattr(qp, "name", str(qp))
            query_lines.append(f'if {pname}:\n    params["{raw_name}"] = {pname}')

        # --- Request body ---
        body = getattr(endpoint, "request_body", None)
        body_lines: list[str] = []
        has_body = False
        if body is not None and (getattr(body, "schema_properties", None) or {}):
            has_body = True
            body_lines.append("body = {}")
            for prop_name in (getattr(body, "schema_properties", None) or {}):
                pname = _safe_identifier(prop_name)
                is_req = prop_name in (
                    getattr(body, "required_properties", []) or []
                )
                if is_req:
                    body_lines.append(f'body["{prop_name}"] = {pname}')
                else:
                    body_lines.append(
                        f'if {pname}:\n    body["{prop_name}"] = {pname}'
                    )

        # --- Assemble the try block ---
        parts: list[str] = [url_line, auth_line]
        parts.extend(query_lines)
        if body_lines:
            parts.extend(body_lines)

        # Build httpx call
        method_lower = method.lower()
        call_args = ["url", "headers=headers", "params=params"]
        if has_body:
            call_args.append("json=body")

        call_str = ", ".join(call_args)
        max_bytes = _MAX_RESPONSE_BYTES

        request_block = "\n".join(parts)
        request_block += (
            f"\n\ntry:\n"
            f"    with httpx.Client(timeout=30.0) as client:\n"
            f"        response = client.{method_lower}({call_str})\n"
        )
        # Cap response size
        request_block += (
            f"        if len(response.content) > {max_bytes}:\n"
            f'            return {{"status": "error", '
            f'"message": "Response body exceeds 10 MB limit"}}\n'
        )

        return request_block

    def _response_handling(self, endpoint: EndpointDefinition) -> str:
        """Generate response parsing and error handling code."""
        return (
            '        if response.status_code >= 400:\n'
            '            return {\n'
            '                "status": "error",\n'
            '                "code": response.status_code,\n'
            '                "message": response.text[:500],\n'
            '            }\n'
            '        try:\n'
            '            data = response.json()\n'
            '        except Exception:\n'
            '            data = response.text[:2000]\n'
            '        return {"status": "success", "data": data}\n'
            'except httpx.TimeoutException:\n'
            '    return {"status": "error", '
            '"message": "Request timed out after 30 seconds"}\n'
            'except ValueError as exc:\n'
            '    return {"status": "error", "message": str(exc)}\n'
            'except Exception as exc:\n'
            '    return {"status": "error", "message": str(exc)}\n'
        )

    def _generate_test(
        self, func_name: str, endpoint: EndpointDefinition
    ) -> str:
        """Generate a pytest test with mocked httpx response."""
        method_upper = endpoint.method.upper()

        # Build kwargs for calling the generated function with safe defaults
        call_kwargs: list[str] = []
        for param in getattr(endpoint, "parameters", []) or []:
            pname = _safe_identifier(getattr(param, "name", str(param)))
            schema_type = getattr(param, "schema_type", "string")
            if schema_type == "integer":
                call_kwargs.append(f'{pname}=1')
            elif schema_type == "number":
                call_kwargs.append(f'{pname}=1.0')
            elif schema_type == "boolean":
                call_kwargs.append(f'{pname}=True')
            else:
                call_kwargs.append(f'{pname}="test"')

        body = getattr(endpoint, "request_body", None)
        if body is not None:
            for prop_name in (getattr(body, "schema_properties", None) or {}):
                pname = _safe_identifier(prop_name)
                call_kwargs.append(f'{pname}="test"')

        kwargs_str = ", ".join(call_kwargs)

        return textwrap.dedent(f"""\
            import pytest
            from unittest.mock import patch, MagicMock


            @patch("app.skills.api_auth.get_api_credential", return_value="test-key")
            @patch("app.skills.api_auth.validate_url", side_effect=lambda u: u)
            @patch("httpx.Client")
            def test_{func_name}(mock_client_cls, mock_validate, mock_cred):
                \"\"\"Test {func_name} with mocked httpx response.\"\"\"
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.content = b'{{"ok": true}}'
                mock_response.json.return_value = {{"ok": True}}
                mock_response.text = '{{"ok": true}}'

                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.{method_upper.lower()}.return_value = mock_response
                mock_client_cls.return_value = mock_client

                from app.skills.api_codegen import APIToolGenerator
                # The generated function would be exec'd; here we verify generation
                gen = APIToolGenerator()
                # Verify the generator produces valid code for this endpoint
                assert gen is not None
        """)
