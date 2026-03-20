"""OpenAPI/Swagger documentation configuration for Pikar AI API.

This module extends FastAPI's auto-generated OpenAPI schema with
additional documentation, examples, and metadata.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced documentation.

    Args:
        app: FastAPI application instance

    Returns:
        Custom OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Pikar AI API",
        version="1.0.0",
        description="""
        # Pikar AI - Multi-Agent Executive System
        
        Pikar AI is a sophisticated multi-agent "Chief of Staff" system built on 
        Google's Agent Development Kit (ADK) with the A2A (Agent-to-Agent) Protocol.
        
        ## Key Features
        
        - **Multi-Agent Orchestration**: Executive Agent coordinates 10+ specialized agents
        - **Knowledge Vault**: RAG-powered semantic search across business knowledge
        - **Workflow Engine**: Automated business process management
        - **A2A Protocol**: Interoperability with external agents
        - **Real-time Widgets**: Interactive UI components for data visualization
        
        ## Architecture
        
        ```
        ExecutiveAgent (Orchestrator)
        ├── Financial Analysis Agent
        ├── Content Creation Agent
        ├── Strategic Planning Agent
        ├── Sales Intelligence Agent
        ├── Marketing Automation Agent
        ├── Operations Optimization Agent
        ├── HR Recruitment Agent
        ├── Compliance Risk Agent
        ├── Customer Support Agent
        └── Data Analysis Agent
        ```
        
        ## Authentication
        
        All API endpoints (except health checks) require authentication via:
        - JWT Bearer token in Authorization header
        - Session-based authentication via cookies
        
        ## Rate Limiting
        
        API endpoints are rate-limited based on user persona:
        - Standard users: 100 requests/minute
        - Premium users: 500 requests/minute
        
        ## Response Format
        
        All responses follow a standard format:
        ```json
        {
            "success": true,
            "data": { ... },
            "message": "Optional message"
        }
        ```
        
        ## Error Handling
        
        Errors follow RFC 7807 (Problem Details) format:
        ```json
        {
            "type": "https://api.pikar.ai/errors/validation",
            "title": "Validation Error",
            "status": 400,
            "detail": "Invalid input data"
        }
        ```
        """,
        routes=app.routes,
    )

    # Add custom tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "Vault",
            "description": "Knowledge Vault operations - document management and semantic search",
        },
        {
            "name": "Workflows",
            "description": "Workflow management - templates, execution, and approvals",
        },
        {
            "name": "Onboarding",
            "description": "User onboarding and persona management",
        },
        {
            "name": "A2A",
            "description": "A2A Protocol endpoints for agent-to-agent communication",
        },
        {
            "name": "MCP",
            "description": "Model Context Protocol - integration management",
        },
    ]

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from authentication endpoint",
        },
        "cookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "session",
            "description": "Session cookie for browser-based authentication",
        },
    }

    # Add common response schemas
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "format": "uri",
                "description": "A URI reference that identifies the problem type",
            },
            "title": {
                "type": "string",
                "description": "A short, human-readable summary of the problem",
            },
            "status": {
                "type": "integer",
                "description": "The HTTP status code",
            },
            "detail": {
                "type": "string",
                "description": "A human-readable explanation specific to this occurrence",
            },
            "instance": {
                "type": "string",
                "format": "uri",
                "description": "A URI reference that identifies the specific occurrence",
            },
        },
        "required": ["title", "status"],
    }

    openapi_schema["components"]["schemas"]["SuccessResponse"] = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "example": True,
            },
            "data": {
                "type": "object",
                "description": "Response payload",
            },
            "message": {
                "type": "string",
                "description": "Optional human-readable message",
            },
        },
        "required": ["success"],
    }

    # Add common parameters
    openapi_schema["components"]["parameters"] = {
        "UserId": {
            "name": "user_id",
            "in": "query",
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
            "description": "Unique user identifier",
        },
        "PageLimit": {
            "name": "limit",
            "in": "query",
            "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100},
            "description": "Number of items to return per page",
        },
        "PageOffset": {
            "name": "offset",
            "in": "query",
            "schema": {"type": "integer", "default": 0, "minimum": 0},
            "description": "Number of items to skip",
        },
    }

    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Full Documentation",
        "url": "https://docs.pikar.ai",
    }

    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "/api/v1",
            "description": "Production API",
        },
        {
            "url": "http://localhost:8000/api/v1",
            "description": "Local Development",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def configure_openapi(app: FastAPI) -> None:
    """Configure FastAPI app with custom OpenAPI schema.

    Args:
        app: FastAPI application instance
    """
    app.openapi = lambda: custom_openapi(app)


# Re-export for convenience
__all__ = ["configure_openapi", "custom_openapi"]
