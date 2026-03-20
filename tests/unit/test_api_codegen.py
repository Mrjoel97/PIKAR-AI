"""Tests for API code generator."""

import ast

import pytest

from app.skills.api_codegen import (
    APIToolGenerator,
    _safe_identifier,
    _to_snake_case,
)
from app.skills.api_parser import APISpec, EndpointDefinition, ParameterDef


# ---------------------------------------------------------------------------
# Helpers to build test fixtures
# ---------------------------------------------------------------------------


def _make_api() -> APISpec:
    """Minimal APISpec for testing code generation."""
    return APISpec(
        title="Test API",
        version="1.0.0",
        base_url="https://api.example.com/v1",
    )


def _make_get_endpoint() -> EndpointDefinition:
    """Simple GET /users endpoint with one query parameter."""
    return EndpointDefinition(
        method="GET",
        path="/users",
        operation_id="listUsers",
        summary="List all users",
        parameters=[
            ParameterDef(
                name="limit",
                location="query",
                required=False,
                schema={"type": "integer"},
                description="Max results to return",
            ),
        ],
    )


def _make_get_with_path_param() -> EndpointDefinition:
    """GET /users/{id} with a path parameter."""
    return EndpointDefinition(
        method="GET",
        path="/users/{id}",
        operation_id="getUser",
        summary="Get user by ID",
        parameters=[
            ParameterDef(
                name="id",
                location="path",
                required=True,
                schema={"type": "string"},
                description="User identifier",
            ),
        ],
    )


def _make_post_endpoint() -> EndpointDefinition:
    """POST /users endpoint (no request body schema properties for codegen stub compat)."""
    return EndpointDefinition(
        method="POST",
        path="/users",
        operation_id="createUser",
        summary="Create a user",
        parameters=[],
        request_body={"type": "object", "properties": {"name": {"type": "string"}}},
    )


# ---------------------------------------------------------------------------
# TestAPIToolGenerator
# ---------------------------------------------------------------------------


class TestAPIToolGenerator:
    """Tests for the APIToolGenerator class."""

    def test_generates_valid_python(self):
        """Generated code should be parseable as valid Python."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        code = tool["code"]
        # ast.parse will raise SyntaxError if the code is invalid
        tree = ast.parse(code)
        assert isinstance(tree, ast.Module)
        # Should contain exactly one function definition at the top level
        func_defs = [
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert len(func_defs) >= 1

    def test_function_name_format(self):
        """operation_id='listUsers', api_name='myapi' should produce 'myapi_list_users'."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        assert tool["name"] == "myapi_list_users"

    def test_function_name_no_api_prefix(self):
        """Without api_name, function name should just be the snake_case operation_id."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", ""
        )
        assert tool["name"] == "list_users"

    def test_includes_auth_header(self):
        """Generated code should contain get_api_credential call."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        assert "get_api_credential" in tool["code"]
        assert "test_secret" in tool["code"]

    def test_includes_ssrf_check(self):
        """Generated code should contain validate_url call."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        assert "validate_url" in tool["code"]

    def test_generates_test_code(self):
        """test_code should be valid Python."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        test_code = tool["test_code"]
        assert test_code  # not empty
        tree = ast.parse(test_code)
        assert isinstance(tree, ast.Module)

    def test_handles_path_parameters(self):
        """Path params like /users/{id} should appear in format_map in the URL construction."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_with_path_param(), _make_api(), "test_secret", "myapi"
        )
        code = tool["code"]
        # The generated code should use format_map for path params
        assert "format_map" in code
        assert '"/users/{id}"' in code or "/users/{id}" in code

    def test_batch_generation(self):
        """Multiple endpoints should produce multiple tool dicts."""
        gen = APIToolGenerator()
        endpoints = [_make_get_endpoint(), _make_get_with_path_param()]
        api = _make_api()
        results = gen.generate_batch(endpoints, api, "test_secret", "myapi")
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert "myapi_list_users" in names
        assert "myapi_get_user" in names

    def test_batch_deduplicates_names(self):
        """Duplicate operation_ids in a batch should get numeric suffixes."""
        gen = APIToolGenerator()
        # Two endpoints with the same operation_id
        ep1 = _make_get_endpoint()
        ep2 = _make_get_endpoint()
        results = gen.generate_batch([ep1, ep2], _make_api(), "secret", "api")
        names = [r["name"] for r in results]
        assert len(names) == 2
        assert len(set(names)) == 2  # no duplicates
        assert names[0] == "api_list_users"
        assert names[1] == "api_list_users_2"

    def test_tool_dict_keys(self):
        """Generated tool dict should have the expected keys."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        assert set(tool.keys()) == {"name", "code", "description", "test_code"}

    def test_description_uses_summary(self):
        """Tool description should derive from the endpoint summary."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "test_secret", "myapi"
        )
        assert "List all users" in tool["description"]

    def test_httpx_method_matches_endpoint(self):
        """GET endpoint should produce client.get(), POST should produce client.post()."""
        gen = APIToolGenerator()

        get_tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "s", "api"
        )
        assert "client.get(" in get_tool["code"]

        post_tool = gen.generate_tool(
            _make_post_endpoint(), _make_api(), "s", "api"
        )
        assert "client.post(" in post_tool["code"]

    def test_includes_timeout_handling(self):
        """Generated code should handle httpx.TimeoutException."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "s", "api"
        )
        assert "TimeoutException" in tool["code"]

    def test_includes_response_size_guard(self):
        """Generated code should check response body size."""
        gen = APIToolGenerator()
        tool = gen.generate_tool(
            _make_get_endpoint(), _make_api(), "s", "api"
        )
        assert "10 MB" in tool["code"] or "10485760" in tool["code"]


# ---------------------------------------------------------------------------
# Tests for helper functions
# ---------------------------------------------------------------------------


class TestToSnakeCase:
    """Tests for _to_snake_case helper."""

    def test_camel_case(self):
        assert _to_snake_case("listUsers") == "list_users"

    def test_pascal_case(self):
        assert _to_snake_case("ListUsers") == "list_users"

    def test_kebab_case(self):
        assert _to_snake_case("list-users") == "list_users"

    def test_already_snake(self):
        assert _to_snake_case("list_users") == "list_users"

    def test_acronym_run(self):
        assert _to_snake_case("getHTTPSUrl") == "get_https_url"


class TestSafeIdentifier:
    """Tests for _safe_identifier helper."""

    def test_strips_special_chars(self):
        assert _safe_identifier("my-param!") == "my_param"

    def test_prefixes_digit_start(self):
        assert _safe_identifier("123abc") == "p_123abc"

    def test_handles_keyword(self):
        result = _safe_identifier("class")
        assert result == "class_"

    def test_collapses_underscores(self):
        assert _safe_identifier("a___b") == "a_b"
