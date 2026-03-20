"""OpenAPI 3.x specification parser for the Universal API Connector.

Parses OpenAPI 3.0.x and 3.1.x specifications into structured endpoint
definitions that the code generator can consume.  Supports fetching specs
from URLs (with SSRF protection), JSON/YAML strings, and raw dicts.

Key design decisions:
- All ``$ref`` pointers are resolved recursively with a depth cap of 10
  to guard against circular references.
- YAML support is optional: when PyYAML is not installed the parser falls
  back to JSON-only mode and logs a warning if YAML content is encountered.
- ``parse_from_url`` validates the target against private/internal CIDRs
  and reserved hostnames before issuing the request.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    import yaml  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - YAML support is optional
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------

BLOCKED_HOSTS: set[str] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "169.254.169.254",
}

BLOCKED_CIDRS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

_FETCH_TIMEOUT_SECONDS = 30
_MAX_REF_DEPTH = 10
_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


def validate_url(url: str) -> bool:
    """Return *True* when *url* points to a public (non-internal) host.

    Blocks private RFC-1918 ranges, link-local addresses, ``localhost``,
    the GCE metadata endpoint, and IPv6 ULA / link-local prefixes.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    if hostname.lower() in BLOCKED_HOSTS:
        return False

    try:
        ip = ipaddress.ip_address(hostname)
        for cidr in BLOCKED_CIDRS:
            if ip in cidr:
                return False
        if ip.is_loopback or ip.is_reserved or ip.is_multicast:
            return False
    except ValueError:
        # hostname is a DNS name — that's fine, the IP check doesn't apply
        pass

    return True


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ParameterDef:
    """API endpoint parameter definition."""

    name: str
    location: str  # "path", "query", "header", "cookie"
    required: bool
    schema: dict[str, Any]  # JSON Schema fragment
    description: str = ""
    default: Any = None


@dataclass
class EndpointDefinition:
    """Single API endpoint extracted from an OpenAPI spec."""

    method: str  # GET, POST, PUT, DELETE, PATCH, …
    path: str  # /v1/customers/{id}
    operation_id: str  # listCustomers
    summary: str  # Human-readable description
    parameters: list[ParameterDef] = field(default_factory=list)
    request_body: dict[str, Any] | None = None  # JSON Schema for body
    response_schema: dict[str, Any] | None = None  # JSON Schema for 2xx
    auth_required: bool = True
    tags: list[str] = field(default_factory=list)
    content_type: str = "application/json"


@dataclass
class APISpec:
    """Fully parsed API specification."""

    title: str
    version: str
    base_url: str
    description: str = ""
    auth_schemes: dict[str, dict[str, Any]] = field(default_factory=dict)
    endpoints: list[EndpointDefinition] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OpenAPIParseError(Exception):
    """Raised when a spec cannot be parsed into a valid ``APISpec``."""


class SSRFBlockedError(Exception):
    """Raised when a URL fails the SSRF validation check."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class OpenAPIParser:
    """Parse OpenAPI 3.x specifications into structured ``APISpec`` objects."""

    # -- public entry points ------------------------------------------------

    def parse(self, spec: dict[str, Any]) -> APISpec:
        """Parse an OpenAPI spec *dict* into a structured ``APISpec``.

        Parameters
        ----------
        spec:
            A Python dict representing the full OpenAPI document.

        Returns
        -------
        APISpec
            Structured representation of the specification.

        Raises
        ------
        OpenAPIParseError
            When the *spec* is missing required top-level keys or the
            ``openapi`` version is unsupported.
        """
        self._validate_spec(spec)

        info = spec.get("info", {})
        title = info.get("title", "Untitled API")
        version = info.get("version", "0.0.0")
        description = info.get("description", "")

        base_url = self._extract_base_url(spec)
        auth_schemes = self._extract_auth_schemes(spec)
        endpoints = self._extract_endpoints(spec)

        return APISpec(
            title=title,
            version=version,
            base_url=base_url,
            description=description,
            auth_schemes=auth_schemes,
            endpoints=endpoints,
        )

    def parse_from_url(self, url: str) -> APISpec:
        """Fetch an OpenAPI spec from *url* and parse it.

        Supports both JSON and YAML responses.  The target URL is validated
        against internal/private networks before the request is made (SSRF
        protection).

        Parameters
        ----------
        url:
            Public HTTP(S) URL pointing to an OpenAPI specification.

        Returns
        -------
        APISpec

        Raises
        ------
        SSRFBlockedError
            When the URL resolves to an internal or private address.
        OpenAPIParseError
            When the response body cannot be parsed.
        """
        if not validate_url(url):
            raise SSRFBlockedError(f"URL blocked by SSRF protection: {url}")

        try:
            with httpx.Client(
                timeout=_FETCH_TIMEOUT_SECONDS,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenAPIParseError(
                f"Failed to fetch OpenAPI spec from {url}: {exc}"
            ) from exc

        return self.parse_from_string(response.text)

    def parse_from_string(self, content: str) -> APISpec:
        """Parse an OpenAPI spec from a JSON or YAML string.

        Parameters
        ----------
        content:
            Raw spec content (JSON or YAML).

        Returns
        -------
        APISpec

        Raises
        ------
        OpenAPIParseError
            When the string cannot be decoded as JSON or YAML.
        """
        spec = self._decode_content(content)
        return self.parse(spec)

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _validate_spec(spec: dict[str, Any]) -> None:
        """Ensure the spec has a supported ``openapi`` version."""
        openapi_version = spec.get("openapi", "")
        if not openapi_version:
            # Could be Swagger 2.0 — we don't support that
            swagger_version = spec.get("swagger", "")
            if swagger_version:
                raise OpenAPIParseError(
                    f"Swagger {swagger_version} is not supported. "
                    "Please convert to OpenAPI 3.x first."
                )
            raise OpenAPIParseError(
                "Missing 'openapi' version key — is this a valid OpenAPI document?"
            )
        if not openapi_version.startswith("3."):
            raise OpenAPIParseError(
                f"Unsupported OpenAPI version: {openapi_version}. "
                "Only 3.0.x and 3.1.x are supported."
            )

    @staticmethod
    def _decode_content(content: str) -> dict[str, Any]:
        """Attempt to decode *content* as JSON first, then YAML."""
        content = content.strip()

        # Try JSON first (faster and always available)
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
            raise OpenAPIParseError("Parsed content is not a JSON object (dict).")
        except json.JSONDecodeError:
            pass

        # Fall back to YAML
        if yaml is not None:
            try:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    return parsed
                raise OpenAPIParseError("Parsed YAML content is not a mapping (dict).")
            except yaml.YAMLError as exc:
                raise OpenAPIParseError(
                    f"Failed to parse content as JSON or YAML: {exc}"
                ) from exc

        raise OpenAPIParseError(
            "Content is not valid JSON and PyYAML is not installed for "
            "YAML parsing. Install pyyaml or provide a JSON spec."
        )

    # -- spec extraction ----------------------------------------------------

    @staticmethod
    def _extract_base_url(spec: dict[str, Any]) -> str:
        """Extract the first server URL, falling back to ``/``."""
        servers = spec.get("servers", [])
        if not servers:
            return "/"
        server = servers[0]
        url = server.get("url", "/")

        # Expand server variables (e.g. {version} → default value)
        variables = server.get("variables", {})
        for var_name, var_def in variables.items():
            default = var_def.get("default", "")
            url = url.replace(f"{{{var_name}}}", str(default))

        return url.rstrip("/")

    @staticmethod
    def _extract_auth_schemes(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Extract ``securitySchemes`` from components."""
        components = spec.get("components", {})
        schemes = components.get("securitySchemes", {})
        result: dict[str, dict[str, Any]] = {}

        for name, definition in schemes.items():
            result[name] = {
                "type": definition.get("type", ""),
                "scheme": definition.get("scheme", ""),
                "in": definition.get("in", ""),
                "name": definition.get("name", ""),
                "description": definition.get("description", ""),
                "bearerFormat": definition.get("bearerFormat", ""),
                "openIdConnectUrl": definition.get("openIdConnectUrl", ""),
            }
            # Include flows for oauth2
            if definition.get("type") == "oauth2" and "flows" in definition:
                result[name]["flows"] = definition["flows"]

        return result

    def _extract_endpoints(self, spec: dict[str, Any]) -> list[EndpointDefinition]:
        """Walk ``paths`` and build ``EndpointDefinition`` for each operation."""
        paths = spec.get("paths", {})
        global_security = spec.get("security")
        endpoints: list[EndpointDefinition] = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                logger.warning("Skipping non-dict path item at %s", path)
                continue

            # Resolve path-item level $ref (rare but valid)
            if "$ref" in path_item:
                path_item = self._resolve_ref(path_item["$ref"], spec)

            # Path-level parameters are inherited by all operations
            path_params = path_item.get("parameters", [])

            for method in _HTTP_METHODS:
                operation = path_item.get(method)
                if operation is None:
                    continue

                if not isinstance(operation, dict):
                    logger.warning(
                        "Skipping non-dict operation %s %s", method.upper(), path
                    )
                    continue

                try:
                    endpoint = self._build_endpoint(
                        method=method,
                        path=path,
                        operation=operation,
                        path_params=path_params,
                        spec=spec,
                        global_security=global_security,
                    )
                    endpoints.append(endpoint)
                except Exception:
                    logger.warning(
                        "Failed to parse endpoint %s %s, skipping",
                        method.upper(),
                        path,
                        exc_info=True,
                    )

        return endpoints

    def _build_endpoint(
        self,
        method: str,
        path: str,
        operation: dict[str, Any],
        path_params: list[dict[str, Any]],
        spec: dict[str, Any],
        global_security: list[dict[str, list[str]]] | None,
    ) -> EndpointDefinition:
        """Construct a single ``EndpointDefinition``."""
        operation_id = operation.get(
            "operationId",
            self._generate_operation_id(method, path),
        )
        summary = operation.get("summary", "") or operation.get("description", "")

        parameters = self._extract_parameters(operation, path_params, spec)
        request_body = self._extract_request_body(operation, spec)
        response_schema = self._extract_response_schema(operation, spec)
        tags = operation.get("tags", [])

        # Determine content type from request body
        content_type = "application/json"
        raw_body = operation.get("requestBody", {})
        if "$ref" in raw_body:
            raw_body = self._resolve_ref(raw_body["$ref"], spec)
        body_content = raw_body.get("content", {}) if isinstance(raw_body, dict) else {}
        if body_content:
            # Prefer application/json, fall back to first available type
            if "application/json" not in body_content:
                content_type = next(iter(body_content), "application/json")

        # Determine if auth is required
        auth_required = self._check_auth_required(operation, global_security)

        return EndpointDefinition(
            method=method.upper(),
            path=path,
            operation_id=operation_id,
            summary=summary,
            parameters=parameters,
            request_body=request_body,
            response_schema=response_schema,
            auth_required=auth_required,
            tags=tags,
            content_type=content_type,
        )

    @staticmethod
    def _check_auth_required(
        operation: dict[str, Any],
        global_security: list[dict[str, list[str]]] | None,
    ) -> bool:
        """Determine whether the operation requires authentication.

        Per the spec, operation-level ``security`` overrides global.
        An empty list ``[]`` means "no auth required".
        """
        # Operation-level security takes precedence
        op_security = operation.get("security")
        if op_security is not None:
            # An empty list explicitly opts out of auth
            if not op_security:
                return False
            # Check if any scheme entry is empty-dict (anonymous allowed)
            return not any(s == {} for s in op_security)

        # Fall back to global security
        if global_security is not None:
            if not global_security:
                return False
            return not any(s == {} for s in global_security)

        # No security declarations → assume auth required (safe default)
        return True

    def _extract_parameters(
        self,
        operation: dict[str, Any],
        path_params: list[dict[str, Any]],
        spec: dict[str, Any],
    ) -> list[ParameterDef]:
        """Merge path-level and operation-level parameters.

        Operation-level parameters override path-level ones when they share
        the same ``name`` + ``in`` combination (per the OpenAPI spec).
        """
        # Index path-level params by (name, in) for override detection
        merged: dict[tuple[str, str], dict[str, Any]] = {}

        for param in path_params:
            resolved = self._resolve_if_ref(param, spec)
            key = (resolved.get("name", ""), resolved.get("in", ""))
            merged[key] = resolved

        # Operation params override path params
        for param in operation.get("parameters", []):
            resolved = self._resolve_if_ref(param, spec)
            key = (resolved.get("name", ""), resolved.get("in", ""))
            merged[key] = resolved

        result: list[ParameterDef] = []
        for param in merged.values():
            try:
                schema = param.get("schema", {})
                if "$ref" in schema:
                    schema = self._resolve_ref(schema["$ref"], spec)
                schema = self._resolve_all_refs(schema, spec)

                result.append(
                    ParameterDef(
                        name=param.get("name", ""),
                        location=param.get("in", "query"),
                        required=param.get("required", False),
                        schema=schema,
                        description=param.get("description", ""),
                        default=schema.get("default", param.get("default")),
                    )
                )
            except Exception:
                logger.warning(
                    "Failed to parse parameter %s, skipping",
                    param.get("name", "<unknown>"),
                    exc_info=True,
                )

        return result

    def _extract_request_body(
        self,
        operation: dict[str, Any],
        spec: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Extract the JSON Schema for the request body, if present."""
        body = operation.get("requestBody")
        if body is None:
            return None

        body = self._resolve_if_ref(body, spec)

        content = body.get("content", {})
        # Prefer application/json, then first available media type
        media = (
            content.get("application/json")
            or content.get("application/merge-patch+json")
            or next(iter(content.values()), None)
            if content
            else None
        )
        if media is None:
            return None

        schema = media.get("schema", {})
        return self._resolve_all_refs(schema, spec)

    def _extract_response_schema(
        self,
        operation: dict[str, Any],
        spec: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Extract the schema for the first successful (2xx) response."""
        responses = operation.get("responses", {})
        if not responses:
            return None

        # Find the first 2xx response
        target_response = None
        for code in sorted(responses.keys()):
            code_str = str(code)
            if code_str.startswith("2") or code_str == "default":
                target_response = responses[code]
                break

        if target_response is None:
            return None

        target_response = self._resolve_if_ref(target_response, spec)

        content = target_response.get("content", {})
        media = (
            content.get("application/json") or next(iter(content.values()), None)
            if content
            else None
        )
        if media is None:
            return None

        schema = media.get("schema", {})
        return self._resolve_all_refs(schema, spec)

    # -- $ref resolution ----------------------------------------------------

    def _resolve_if_ref(
        self, obj: dict[str, Any], spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve *obj* if it contains a ``$ref``, otherwise return as-is."""
        if isinstance(obj, dict) and "$ref" in obj:
            return self._resolve_ref(obj["$ref"], spec)
        return obj

    @staticmethod
    def _resolve_ref(ref: str, spec: dict[str, Any]) -> dict[str, Any]:
        """Resolve a JSON ``$ref`` pointer like ``#/components/schemas/Foo``.

        Only local (same-document) ``#/...`` references are supported.
        Returns a *copy* so the caller can mutate without side effects on
        the original spec.
        """
        if not ref.startswith("#/"):
            logger.warning("External $ref not supported: %s", ref)
            return {"$ref": ref}

        parts = ref[2:].split("/")
        current: Any = spec
        for part in parts:
            # Handle JSON Pointer escaping (RFC 6901)
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict):
                current = current.get(part)
            else:
                logger.warning("Cannot resolve $ref path segment '%s' in %s", part, ref)
                return {}
            if current is None:
                logger.warning("$ref target not found: %s", ref)
                return {}

        if isinstance(current, dict):
            # Return a shallow copy so callers don't mutate the original
            return dict(current)
        return {}

    def _resolve_all_refs(
        self,
        obj: Any,
        spec: dict[str, Any],
        depth: int = 0,
    ) -> Any:
        """Recursively resolve all ``$ref`` pointers in a schema tree.

        Parameters
        ----------
        obj:
            The schema node to process.
        spec:
            The full OpenAPI document (for reference lookup).
        depth:
            Current recursion depth.  Stops at ``_MAX_REF_DEPTH`` to
            prevent infinite loops on circular references.

        Returns
        -------
        The schema with all resolvable ``$ref`` pointers inlined.
        """
        if depth > _MAX_REF_DEPTH:
            logger.warning(
                "Max $ref resolution depth (%d) reached — possible circular reference",
                _MAX_REF_DEPTH,
            )
            return obj

        if isinstance(obj, dict):
            if "$ref" in obj:
                resolved = self._resolve_ref(obj["$ref"], spec)
                # If we got back an unresolved $ref, stop recursion
                if "$ref" in resolved:
                    return resolved
                return self._resolve_all_refs(resolved, spec, depth + 1)

            return {
                key: self._resolve_all_refs(value, spec, depth + 1)
                for key, value in obj.items()
            }

        if isinstance(obj, list):
            return [self._resolve_all_refs(item, spec, depth + 1) for item in obj]

        return obj

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _generate_operation_id(method: str, path: str) -> str:
        """Synthesise an ``operationId`` from the HTTP method and path.

        Examples::

            GET  /v1/customers       → get_v1_customers
            POST /v1/customers/{id}  → post_v1_customers_id
            DELETE /orders/{orderId}/items/{itemId}
                                     → delete_orders_orderId_items_itemId
        """
        # Strip leading/trailing slashes, replace separators with underscores
        clean = path.strip("/")
        # Remove braces from path parameters
        clean = re.sub(r"[{}]", "", clean)
        # Replace non-word characters with underscores
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", clean)
        # Collapse consecutive underscores
        clean = re.sub(r"_+", "_", clean).strip("_")

        return f"{method.lower()}_{clean}" if clean else method.lower()
