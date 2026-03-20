"""Tests for OpenAPI parser."""

import copy
import json

import pytest

from app.skills.api_parser import (
    APISpec,
    EndpointDefinition,
    OpenAPIParseError,
    OpenAPIParser,
    ParameterDef,
    SSRFBlockedError,
    validate_url,
)

# ---------------------------------------------------------------------------
# Sample minimal OpenAPI 3.0 spec for testing
# ---------------------------------------------------------------------------

SAMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List all users",
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                }
                            }
                        }
                    }
                },
            },
            "post": {
                "operationId": "createUser",
                "summary": "Create a user",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}},
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "content": {
                            "application/json": {"schema": {"type": "object"}}
                        }
                    }
                },
            },
        },
        "/users/{id}": {
            "get": {
                "operationId": "getUser",
                "summary": "Get user by ID",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"schema": {"type": "object"}}
                        }
                    }
                },
            }
        },
    },
}


# ---------------------------------------------------------------------------
# TestOpenAPIParser
# ---------------------------------------------------------------------------


class TestOpenAPIParser:
    """Tests for the OpenAPIParser class."""

    def test_parses_basic_spec(self):
        """Parse a minimal OpenAPI 3.0 spec and verify top-level fields."""
        parser = OpenAPIParser()
        result = parser.parse(SAMPLE_SPEC)
        assert isinstance(result, APISpec)
        assert result.title == "Test API"
        assert result.version == "1.0.0"
        assert result.base_url == "https://api.example.com/v1"
        assert len(result.endpoints) == 3

    def test_extracts_endpoint_methods(self):
        """GET and POST methods should be extracted from the spec."""
        parser = OpenAPIParser()
        result = parser.parse(SAMPLE_SPEC)
        methods = {e.method for e in result.endpoints}
        assert methods == {"GET", "POST"}

    def test_extracts_parameters(self):
        """Path and query parameters should be extracted correctly."""
        parser = OpenAPIParser()
        result = parser.parse(SAMPLE_SPEC)
        get_user = next(
            e for e in result.endpoints if e.operation_id == "getUser"
        )
        assert any(
            p.name == "id" and p.location == "path" for p in get_user.parameters
        )

        list_users = next(
            e for e in result.endpoints if e.operation_id == "listUsers"
        )
        assert any(
            p.name == "limit" and p.location == "query"
            for p in list_users.parameters
        )

    def test_extracts_request_body(self):
        """createUser endpoint should have a request_body schema."""
        parser = OpenAPIParser()
        result = parser.parse(SAMPLE_SPEC)
        create_user = next(
            e for e in result.endpoints if e.operation_id == "createUser"
        )
        assert create_user.request_body is not None
        assert create_user.request_body.get("type") == "object"
        assert "name" in create_user.request_body.get("properties", {})

    def test_extracts_response_schema(self):
        """200 response schema should be extracted for listUsers."""
        parser = OpenAPIParser()
        result = parser.parse(SAMPLE_SPEC)
        list_users = next(
            e for e in result.endpoints if e.operation_id == "listUsers"
        )
        assert list_users.response_schema is not None
        assert list_users.response_schema.get("type") == "array"

    def test_generates_operation_id_when_missing(self):
        """When operationId is absent, a synthesized ID should be generated."""
        spec = copy.deepcopy(SAMPLE_SPEC)
        # Remove all operationIds
        for path_item in spec["paths"].values():
            for method in ("get", "post", "put", "delete", "patch"):
                op = path_item.get(method)
                if op and "operationId" in op:
                    del op["operationId"]

        parser = OpenAPIParser()
        result = parser.parse(spec)
        op_ids = {e.operation_id for e in result.endpoints}
        # Should contain auto-generated IDs based on method + path
        assert "get_users" in op_ids
        assert "post_users" in op_ids
        assert "get_users_id" in op_ids

    def test_resolves_refs(self):
        """$ref pointers in schemas should be resolved inline."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Ref Test", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    }
                }
            },
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List users",
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/User"
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        ep = result.endpoints[0]
        # The $ref should have been resolved to the actual User schema
        items = ep.response_schema.get("items", {})
        assert items.get("type") == "object"
        assert "name" in items.get("properties", {})

    def test_handles_circular_refs(self):
        """Self-referencing schema should not cause infinite recursion."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Circular Test", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "children": {
                                "type": "array",
                                "items": {
                                    "$ref": "#/components/schemas/Node"
                                },
                            },
                        },
                    }
                }
            },
            "paths": {
                "/nodes": {
                    "get": {
                        "operationId": "listNodes",
                        "summary": "List nodes",
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/Node"
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }

        parser = OpenAPIParser()
        # Should complete without hanging or raising
        result = parser.parse(spec)
        assert len(result.endpoints) == 1
        ep = result.endpoints[0]
        assert ep.response_schema is not None
        assert ep.response_schema.get("type") == "object"

    def test_rejects_swagger_2(self):
        """Swagger 2.0 spec should raise OpenAPIParseError."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Old Spec", "version": "1.0.0"},
            "paths": {},
        }

        parser = OpenAPIParser()
        with pytest.raises(OpenAPIParseError, match="Swagger 2.0 is not supported"):
            parser.parse(spec)

    def test_rejects_missing_openapi_key(self):
        """A spec without 'openapi' key should raise OpenAPIParseError."""
        spec = {
            "info": {"title": "Bad Spec", "version": "1.0.0"},
            "paths": {},
        }

        parser = OpenAPIParser()
        with pytest.raises(OpenAPIParseError, match="Missing 'openapi' version key"):
            parser.parse(spec)

    def test_rejects_unsupported_openapi_version(self):
        """Non-3.x version should raise OpenAPIParseError."""
        spec = {
            "openapi": "4.0.0",
            "info": {"title": "Future Spec", "version": "1.0.0"},
            "paths": {},
        }

        parser = OpenAPIParser()
        with pytest.raises(OpenAPIParseError, match="Unsupported OpenAPI version"):
            parser.parse(spec)

    def test_parses_openapi_31(self):
        """OpenAPI 3.1.x specs should be accepted."""
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Modern Spec", "version": "2.0.0"},
            "paths": {},
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        assert result.title == "Modern Spec"

    def test_no_servers_falls_back_to_slash(self):
        """When 'servers' is absent, base_url should default to '/'."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "No Server", "version": "1.0.0"},
            "paths": {},
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        assert result.base_url == "/"

    def test_server_variable_expansion(self):
        """Server variables should be expanded to their default values."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Var Server", "version": "1.0.0"},
            "servers": [
                {
                    "url": "https://api.example.com/{version}",
                    "variables": {
                        "version": {"default": "v2"},
                    },
                }
            ],
            "paths": {},
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        assert result.base_url == "https://api.example.com/v2"

    def test_extracts_auth_schemes(self):
        """Security schemes should be extracted from components."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Auth Test", "version": "1.0.0"},
            "components": {
                "securitySchemes": {
                    "bearer_auth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    },
                    "api_key": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                }
            },
            "paths": {},
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        assert "bearer_auth" in result.auth_schemes
        assert result.auth_schemes["bearer_auth"]["type"] == "http"
        assert result.auth_schemes["bearer_auth"]["scheme"] == "bearer"
        assert "api_key" in result.auth_schemes
        assert result.auth_schemes["api_key"]["name"] == "X-API-Key"

    def test_parse_from_string_json(self):
        """parse_from_string should accept a JSON string."""
        parser = OpenAPIParser()
        result = parser.parse_from_string(json.dumps(SAMPLE_SPEC))
        assert result.title == "Test API"
        assert len(result.endpoints) == 3

    def test_parse_from_string_invalid_json(self):
        """Invalid JSON/YAML content should raise OpenAPIParseError."""
        parser = OpenAPIParser()
        with pytest.raises(OpenAPIParseError):
            parser.parse_from_string("<<<not json or yaml>>>")

    def test_path_level_params_inherited(self):
        """Path-level parameters should be inherited by operations."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Param Test", "version": "1.0.0"},
            "paths": {
                "/items/{itemId}": {
                    "parameters": [
                        {
                            "name": "itemId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "getItem",
                        "summary": "Get item",
                        "responses": {"200": {}},
                    },
                }
            },
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        ep = result.endpoints[0]
        assert any(p.name == "itemId" and p.location == "path" for p in ep.parameters)

    def test_operation_params_override_path_params(self):
        """Operation-level params should override path-level with same name+in."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Override Test", "version": "1.0.0"},
            "paths": {
                "/items/{id}": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "path-level",
                        }
                    ],
                    "get": {
                        "operationId": "getItem",
                        "summary": "Get item",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                                "description": "operation-level",
                            }
                        ],
                        "responses": {"200": {}},
                    },
                }
            },
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        ep = result.endpoints[0]
        id_param = next(p for p in ep.parameters if p.name == "id")
        # Operation-level override should win
        assert id_param.description == "operation-level"
        assert id_param.schema.get("type") == "integer"

    def test_auth_required_respects_empty_security(self):
        """An empty security list on an operation means no auth required."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Auth Override", "version": "1.0.0"},
            "security": [{"bearer": []}],
            "paths": {
                "/public": {
                    "get": {
                        "operationId": "publicEndpoint",
                        "summary": "Public",
                        "security": [],
                        "responses": {"200": {}},
                    }
                }
            },
        }

        parser = OpenAPIParser()
        result = parser.parse(spec)
        ep = result.endpoints[0]
        assert ep.auth_required is False


# ---------------------------------------------------------------------------
# TestValidateUrl
# ---------------------------------------------------------------------------


class TestValidateUrl:
    """Tests for the SSRF URL validation function."""

    def test_allows_public_urls(self):
        """Public HTTPS URLs should pass validation."""
        assert validate_url("https://api.example.com/spec.json") is True

    def test_allows_public_http(self):
        """Public HTTP URLs should pass validation."""
        assert validate_url("http://api.example.com/spec.json") is True

    def test_blocks_localhost(self):
        """localhost should be blocked."""
        assert validate_url("http://localhost:8080/spec") is False

    def test_blocks_127_0_0_1(self):
        """127.0.0.1 should be blocked."""
        assert validate_url("http://127.0.0.1/spec") is False

    def test_blocks_private_ip_10(self):
        """10.x.x.x range should be blocked."""
        assert validate_url("http://10.0.0.1/spec") is False

    def test_blocks_private_ip_192_168(self):
        """192.168.x.x range should be blocked."""
        assert validate_url("http://192.168.1.1/spec") is False

    def test_blocks_private_ip_172_16(self):
        """172.16.x.x range should be blocked."""
        assert validate_url("http://172.16.0.1/spec") is False

    def test_blocks_metadata_endpoint(self):
        """GCE/AWS metadata endpoint should be blocked."""
        assert validate_url("http://169.254.169.254/latest/meta-data/") is False

    def test_rejects_file_scheme(self):
        """file:// scheme should be rejected."""
        assert validate_url("file:///etc/passwd") is False

    def test_rejects_ftp_scheme(self):
        """ftp:// scheme should be rejected."""
        assert validate_url("ftp://internal.corp/spec") is False

    def test_rejects_empty_url(self):
        """An empty string should be rejected."""
        assert validate_url("") is False

    def test_rejects_no_hostname(self):
        """A URL without a hostname should be rejected."""
        assert validate_url("http://") is False

    def test_blocks_zero_address(self):
        """0.0.0.0 should be blocked."""
        assert validate_url("http://0.0.0.0/spec") is False

    def test_blocks_ipv6_loopback(self):
        """IPv6 loopback (::1) should be blocked."""
        assert validate_url("http://[::1]/spec") is False

    def test_blocks_google_metadata_hostname(self):
        """metadata.google.internal should be blocked."""
        assert validate_url("http://metadata.google.internal/computeMetadata/v1") is False
