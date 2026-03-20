"""Universal API Connector Tools.

ADK tools that allow agents to connect to external APIs by parsing
OpenAPI specs and auto-generating tool wrappers.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def connect_api(
    spec_url: str,
    api_name: str = "",
    secret_name: str = "",
    selected_endpoints: str = "",
) -> dict[str, Any]:
    """Connect to an external API by providing its OpenAPI specification URL.

    Reads the API documentation, generates tool wrappers for the endpoints,
    validates them, and registers them so agents can use them immediately.

    Args:
        spec_url: URL to the OpenAPI/Swagger spec (JSON or YAML).
        api_name: Short name for the API (e.g., 'stripe', 'hubspot').
            Auto-derived from spec title if not provided.
        secret_name: Name of the stored API credential to use for auth.
        selected_endpoints: Comma-separated operation IDs to connect.
            If empty, connects the first 10 endpoints.

    Returns:
        Dict with created_tools list, skipped count, and usage instructions.
    """
    try:
        from app.skills.api_parser import OpenAPIParser, validate_url
    except ImportError:
        return {
            "success": False,
            "error": "API parser module not available yet. The api_parser skill is being set up.",
        }

    # SSRF check
    try:
        if not validate_url(spec_url):
            return {
                "success": False,
                "error": "URL blocked: internal/private network addresses are not allowed",
            }
    except Exception as e:
        return {"success": False, "error": f"URL validation failed: {e!s}"}

    # Parse spec
    try:
        parser = OpenAPIParser()
        api_spec = parser.parse_from_url(spec_url)
    except Exception as e:
        logger.error("Failed to parse OpenAPI spec from %s: %s", spec_url, e, exc_info=True)
        return {"success": False, "error": f"Failed to parse API spec: {e!s}"}

    if not api_spec.endpoints:
        return {"success": False, "error": "No endpoints found in the API spec"}

    # Derive api_name if not provided
    if not api_name:
        api_name = api_spec.title.lower().replace(" ", "_")[:30]
    api_name = re.sub(r"[^a-z0-9_]", "", api_name)

    if not api_name:
        api_name = "api"

    # Filter endpoints
    endpoints = api_spec.endpoints
    if selected_endpoints:
        selected = [s.strip() for s in selected_endpoints.split(",")]
        endpoints = [e for e in endpoints if e.operation_id in selected]
    endpoints = endpoints[:10]  # Cap at 10

    if not endpoints:
        return {
            "success": False,
            "error": "No matching endpoints found after filtering. Check selected_endpoints.",
        }

    # Generate tools
    try:
        from app.skills.api_codegen import APIToolGenerator
    except ImportError:
        return {
            "success": False,
            "error": "API code generator module not available yet. The api_codegen skill is being set up.",
        }

    try:
        generator = APIToolGenerator()
        tools = generator.generate_batch(endpoints, api_spec, secret_name, api_name)
    except Exception as e:
        logger.error("Failed to generate tool code: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to generate tool code: {e!s}"}

    # Validate and register each tool
    import ast

    created = []
    skipped = []

    for tool in tools:
        try:
            ast.parse(tool["code"])  # Syntax check
        except SyntaxError as e:
            skipped.append({"name": tool.get("name", "unknown"), "error": f"Syntax error: {e!s}"})
            continue

        try:
            # Register as custom skill via sync Supabase (ADK tools run in sync context)
            from app.services.supabase_client import get_service_client
            from app.services.request_context import get_current_user_id

            user_id = get_current_user_id() or "system"
            supabase = get_service_client()

            skill_data = {
                "name": tool["name"],
                "description": tool["description"],
                "category": "api_connector",
                "agent_ids": ["EXEC", "SALES", "MKT", "OPS", "FIN", "DATA"],
                "knowledge": tool["code"],
                "is_active": True,
                "created_by": user_id,
                "metadata": {
                    "api_connection": api_name,
                    "spec_url": spec_url,
                    "endpoint": f"{tool.get('method', '')} {tool.get('path', '')}",
                },
            }

            supabase.table("custom_skills").upsert(
                skill_data, on_conflict="name"
            ).execute()

            created.append({"name": tool["name"], "description": tool["description"]})
        except Exception as e:
            skipped.append({"name": tool.get("name", "unknown"), "error": str(e)})

    return {
        "success": True,
        "api_name": api_name,
        "api_title": api_spec.title,
        "created_tools": created,
        "created_count": len(created),
        "skipped_count": len(skipped),
        "skipped": skipped if skipped else None,
        "usage": f"The following tools are now available: {', '.join(t['name'] for t in created)}"
        if created
        else "No tools were created.",
    }


def list_api_connections() -> dict[str, Any]:
    """List all active API connections and their registered tool endpoints.

    Queries the custom_skills table for skills tagged with an api_connection
    in their metadata. Groups results by API name.

    Returns:
        Dict with list of connected APIs and their tool counts.
    """
    try:
        from app.services.supabase_client import get_service_client
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id() or "system"
        supabase = get_service_client()

        response = (
            supabase.table("custom_skills")
            .select("name, description, metadata, is_active")
            .eq("category", "api_connector")
            .eq("is_active", True)
            .execute()
        )

        records = response.data or []

        # Group by api_connection
        connections: dict[str, dict[str, Any]] = {}
        for record in records:
            meta = record.get("metadata") or {}
            api_name = meta.get("api_connection", "unknown")
            if api_name not in connections:
                connections[api_name] = {
                    "api_name": api_name,
                    "spec_url": meta.get("spec_url", ""),
                    "tools": [],
                }
            connections[api_name]["tools"].append({
                "name": record["name"],
                "description": record.get("description", ""),
                "endpoint": meta.get("endpoint", ""),
            })

        connection_list = list(connections.values())
        for conn in connection_list:
            conn["tool_count"] = len(conn["tools"])

        return {
            "success": True,
            "connection_count": len(connection_list),
            "connections": connection_list,
        }

    except Exception as e:
        logger.error("Failed to list API connections: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list API connections: {e!s}"}


def disconnect_api(api_name: str) -> dict[str, Any]:
    """Disconnect an API by deactivating all its registered tool skills.

    Finds all custom skills tagged with the given api_connection name
    and sets them to inactive.

    Args:
        api_name: The API name used during connect_api (e.g., 'stripe').

    Returns:
        Dict with count of deactivated tools.
    """
    if not api_name:
        return {"success": False, "error": "api_name is required"}

    try:
        from app.services.supabase_client import get_service_client

        supabase = get_service_client()

        # Fetch all active api_connector skills and filter by metadata in code
        response = (
            supabase.table("custom_skills")
            .select("id, name, metadata")
            .eq("category", "api_connector")
            .eq("is_active", True)
            .execute()
        )

        records = response.data or []
        matching_ids = []
        matching_names = []
        for record in records:
            meta = record.get("metadata") or {}
            if meta.get("api_connection") == api_name:
                matching_ids.append(record["id"])
                matching_names.append(record["name"])

        if not matching_ids:
            return {
                "success": False,
                "error": f"No active API connection found with name '{api_name}'",
            }

        # Deactivate all matching skills
        deactivated = 0
        for skill_id in matching_ids:
            try:
                supabase.table("custom_skills").update(
                    {"is_active": False}
                ).eq("id", skill_id).execute()
                deactivated += 1
            except Exception as e:
                logger.warning("Failed to deactivate skill %s: %s", skill_id, e)

        return {
            "success": True,
            "api_name": api_name,
            "deactivated_count": deactivated,
            "deactivated_tools": matching_names,
            "message": f"Disconnected '{api_name}': {deactivated} tool(s) deactivated.",
        }

    except Exception as e:
        logger.error("Failed to disconnect API '%s': %s", api_name, e, exc_info=True)
        return {"success": False, "error": f"Failed to disconnect API: {e!s}"}


def validate_api_connection(api_name: str) -> dict[str, Any]:
    """Check if an API connection's spec is still valid.

    Re-fetches the original spec URL and compares endpoint count.
    If endpoints changed significantly, flags the connection as stale.

    Args:
        api_name: The API name used during connect_api (e.g., 'stripe').

    Returns:
        Dict with validation status, original and current endpoint counts.
    """
    if not api_name:
        return {"success": False, "error": "api_name is required"}

    try:
        from app.services.supabase_client import get_service_client

        supabase = get_service_client()

        # Fetch active skills for this connection
        response = (
            supabase.table("custom_skills")
            .select("name, metadata")
            .eq("category", "api_connector")
            .eq("is_active", True)
            .execute()
        )

        records = response.data or []
        matching = [
            r for r in records
            if (r.get("metadata") or {}).get("api_connection") == api_name
        ]

        if not matching:
            return {
                "success": False,
                "error": f"No active API connection found with name '{api_name}'",
            }

        # Get spec URL from the first matching record
        spec_url = (matching[0].get("metadata") or {}).get("spec_url", "")
        if not spec_url:
            return {
                "success": False,
                "error": f"No spec URL stored for API '{api_name}'. Cannot validate.",
            }

        original_endpoint_count = len(matching)

        # Re-fetch and parse the spec
        try:
            from app.skills.api_parser import OpenAPIParser

            parser = OpenAPIParser()
            api_spec = parser.parse_from_url(spec_url)
            current_endpoint_count = len(api_spec.endpoints) if api_spec.endpoints else 0
        except Exception as exc:
            return {
                "success": True,
                "api_name": api_name,
                "status": "error",
                "message": f"Could not re-fetch spec: {exc!s}",
                "spec_url": spec_url,
                "connected_tools": original_endpoint_count,
            }

        # Compare endpoint counts to detect drift
        is_stale = current_endpoint_count != original_endpoint_count
        status = "stale" if is_stale else "healthy"

        return {
            "success": True,
            "api_name": api_name,
            "status": status,
            "spec_url": spec_url,
            "connected_tools": original_endpoint_count,
            "current_spec_endpoints": current_endpoint_count,
            "message": (
                f"Spec has changed ({original_endpoint_count} connected vs "
                f"{current_endpoint_count} in spec). Consider reconnecting."
                if is_stale
                else f"Connection is healthy. {original_endpoint_count} tool(s) active."
            ),
        }

    except Exception as e:
        logger.error("Failed to validate API connection '%s': %s", api_name, e, exc_info=True)
        return {"success": False, "error": f"Failed to validate API connection: {e!s}"}


API_CONNECTOR_TOOLS = [connect_api, list_api_connections, disconnect_api, validate_api_connection]
