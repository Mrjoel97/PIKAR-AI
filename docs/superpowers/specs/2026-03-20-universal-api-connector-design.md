# Universal API Connector (Skill Builder v2) — Design Specification

> **Status:** Approved
> **Date:** 2026-03-20
> **Scope:** Extend the existing Skill Builder to parse API documentation (OpenAPI/Swagger) and auto-generate tool wrappers that agents can use immediately.

---

## Executive Summary

The existing skill system is **production-ready**:
- Skill CRUD with Supabase persistence + user scoping + RLS
- Dynamic hot-loading from Python modules and SKILL.md files
- Agent-aware access control (agent_ids per skill)
- Skill builder tool that generates, validates (pytest), and registers skills
- Tool registry with 200+ tools for workflow engine access

**What's missing:** API schema parsing and automatic code generation. The system can create and manage skills, but a human still has to write the code. The Universal API Connector adds the ability to point at an API spec URL and get working tools automatically.

---

## Part 1: Current Skill System

### What Works

| Component | File | Status |
|-----------|------|--------|
| Skill CRUD | `app/skills/custom_skills_service.py` | Complete |
| Skill Registry | `app/skills/registry.py` | Complete |
| Skill Builder (code gen) | `app/agents/tools/skill_builder.py` | Complete |
| Skill Validator | `app/skills/skill_validator.py` | Complete |
| Agent-aware access | `app/agents/tools/agent_skills.py` | Complete |
| Tool Registry | `app/agents/tools/registry.py` | Complete (200+ tools) |
| External skills | `app/skills/external_skills.py` | Complete (37 skills) |
| Self-improvement | `app/agents/tools/self_improve.py` | Complete |
| MCP integration | `app/mcp/connector.py` | Complete (PII filter, audit) |

### What's Missing

| Component | Gap |
|-----------|-----|
| API Schema Parsing | No OpenAPI/Swagger parser |
| Endpoint Discovery | Can't read API docs automatically |
| Schema → Skill Conversion | No automatic input/output mapping |
| API Auth Handling | Not generalized for arbitrary APIs |
| Rate Limiting for APIs | Circuit breaker exists for Redis, not for HTTP calls |
| Secret Management | Env vars only, no per-user API key storage |
| SSRF Protection | Generated tools would call any URL |

---

## Part 2: Architecture

### High-Level Flow

```
User: "Connect to the Stripe API" (provides spec URL or file)
  ↓
┌────────────────────────────────────┐
│ 1. API Discovery & Schema Parsing  │  ← NEW: app/skills/api_parser.py
│    Parse OpenAPI 3.x spec          │
│    Extract endpoints, auth, schemas│
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│ 2. Endpoint Selection              │  ← Agent picks relevant endpoints
│    Filter by agent domain          │     (or user selects)
│    Estimate complexity             │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│ 3. Tool Code Generation            │  ← NEW: app/skills/api_codegen.py
│    Generate async Python function  │     EXTENDS: skill_builder.py patterns
│    Include auth injection          │
│    Add parameter validation        │
│    Add error handling + retry      │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│ 4. Validation & Testing            │  ← REUSE: skill_builder.py
│    Syntax check (ast.parse)        │
│    Generate + run pytest tests     │
│    Rollback on failure             │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│ 5. Registration                    │  ← REUSE: existing system
│    Store in custom_skills table    │
│    Register in skills_registry     │
│    Add to tool_registry            │
└────────────────────────────────────┘
  ↓
Agent can use the generated tool immediately
```

---

## Part 3: New Components

### 3.1 API Parser (`app/skills/api_parser.py`)

Parses OpenAPI 3.x specs into structured endpoint definitions.

```python
@dataclass
class EndpointDefinition:
    """Single API endpoint extracted from spec."""
    method: str                    # GET, POST, PUT, DELETE, PATCH
    path: str                      # /v1/customers/{id}
    operation_id: str              # listCustomers
    summary: str                   # Human-readable description
    parameters: list[ParameterDef]  # Path, query, header params
    request_body: dict | None      # JSON Schema for request body
    response_schema: dict | None   # JSON Schema for 2xx response
    auth_schemes: list[str]        # ["bearer", "api_key"]
    tags: list[str]                # ["customers", "billing"]

@dataclass
class ParameterDef:
    name: str
    location: str    # path, query, header
    required: bool
    schema: dict     # JSON Schema
    description: str

@dataclass
class APISpec:
    """Parsed API specification."""
    title: str
    version: str
    base_url: str
    auth_schemes: dict[str, dict]   # security scheme definitions
    endpoints: list[EndpointDefinition]

class OpenAPIParser:
    """Parse OpenAPI 3.x specs into EndpointDefinitions."""

    def parse(self, spec: dict | str) -> APISpec:
        """Parse spec from dict or URL/file path."""

    def parse_from_url(self, url: str) -> APISpec:
        """Fetch and parse spec from URL."""

    def _extract_endpoints(self, spec: dict) -> list[EndpointDefinition]:
        """Walk paths and operations."""

    def _resolve_refs(self, schema: dict, spec: dict) -> dict:
        """Resolve $ref pointers in schemas."""

    def _extract_auth(self, spec: dict) -> dict[str, dict]:
        """Extract securitySchemes."""
```

**Supported spec formats:**
- OpenAPI 3.0.x and 3.1.x (JSON and YAML)
- Swagger 2.0 (auto-convert to 3.x internally)

### 3.2 Code Generator (`app/skills/api_codegen.py`)

Generates Python tool functions from endpoint definitions.

```python
class APIToolGenerator:
    """Generate Python tool code from API endpoints."""

    def generate_tool(self, endpoint: EndpointDefinition, api: APISpec, secret_name: str) -> str:
        """Generate a complete Python function for one endpoint.

        Returns Python source code as a string.
        """

    def generate_batch(self, endpoints: list[EndpointDefinition], api: APISpec, secret_name: str) -> list[dict]:
        """Generate tools for multiple endpoints.

        Returns list of {name, code, description, test_code} dicts.
        """

    def _generate_function_signature(self, endpoint: EndpointDefinition) -> str:
        """Map endpoint params to Python function args with type hints."""

    def _generate_request_code(self, endpoint: EndpointDefinition, api: APISpec) -> str:
        """Generate httpx request with auth injection."""

    def _generate_response_handling(self, endpoint: EndpointDefinition) -> str:
        """Generate response parsing + error handling."""

    def _generate_test(self, endpoint: EndpointDefinition) -> str:
        """Generate pytest test with mocked HTTP responses."""
```

**Generated function structure:**
```python
async def list_customers(
    limit: int = 10,
    starting_after: str = "",
) -> dict:
    """List all customers.

    Fetches customers from the Stripe API with pagination support.

    Args:
        limit: Maximum number of customers to return (1-100).
        starting_after: Cursor for pagination.

    Returns:
        Dict with 'data' (list of customers), 'has_more', and 'url'.
    """
    import httpx
    from app.skills.api_auth import get_api_credential

    url = "https://api.stripe.com/v1/customers"
    headers = {"Authorization": f"Bearer {get_api_credential('stripe_api_key')}"}
    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
```

### 3.3 API Auth Handler (`app/skills/api_auth.py`)

Manages authentication credentials for generated tools.

```python
class APICredentialStore:
    """Store and retrieve API credentials per user."""

    async def store_credential(self, user_id: str, name: str, value: str) -> None:
        """Store encrypted credential in Supabase."""

    async def get_credential(self, user_id: str, name: str) -> str | None:
        """Retrieve credential for use in generated tools."""

    async def delete_credential(self, user_id: str, name: str) -> None:
        """Remove a stored credential."""

    async def list_credentials(self, user_id: str) -> list[str]:
        """List credential names (not values) for a user."""


def get_api_credential(secret_name: str) -> str:
    """Runtime credential resolver used by generated tools.

    Checks (in order):
    1. Environment variable: API_SECRET_{name.upper()}
    2. User credential store (requires request context)

    Raises ValueError if not found.
    """
```

**Supported auth schemes:**
- API Key (header or query param)
- Bearer Token
- Basic Auth
- OAuth 2.0 Client Credentials (with token refresh)

### 3.4 ADK Tool (`app/agents/tools/api_connector.py`)

The user-facing tool that agents call.

```python
def connect_api(
    spec_url: str,
    api_name: str = "",
    secret_name: str = "",
    selected_endpoints: str = "",
) -> dict:
    """Connect to an external API by providing its OpenAPI spec URL.

    Reads the API documentation, generates tool wrappers for the endpoints,
    validates them, and registers them so you can use them immediately.

    Args:
        spec_url: URL to the OpenAPI/Swagger spec (JSON or YAML).
        api_name: Short name for the API (e.g., 'stripe', 'hubspot').
            Auto-derived from spec title if not provided.
        secret_name: Name of the stored API credential to use for auth.
            The user must store their API key first via the configuration tools.
        selected_endpoints: Comma-separated operation IDs to connect.
            If empty, connects the most relevant endpoints (max 10).

    Returns:
        Dict with created_tools (list), skipped_endpoints, test_results, and usage instructions.
    """


def list_api_connections() -> dict:
    """List all API connections and their generated tools.

    Returns:
        Dict with connections (list of {api_name, endpoint_count, tools, created_at}).
    """


def disconnect_api(api_name: str) -> dict:
    """Remove all generated tools for an API connection.

    Args:
        api_name: The API name used when connecting.

    Returns:
        Dict with removed_tools count and status.
    """

API_CONNECTOR_TOOLS = [connect_api, list_api_connections, disconnect_api]
```

---

## Part 4: Security

### 4.1 SSRF Protection

```python
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "metadata.google.internal", "169.254.169.254",  # Cloud metadata
}
BLOCKED_CIDRS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]  # Private ranges

def validate_api_url(url: str) -> bool:
    """Reject URLs pointing to internal/private networks."""
```

### 4.2 Generated Code Safety

| Threat | Mitigation |
|--------|-----------|
| Code injection via spec fields | Sanitize all spec strings; escape in generated code |
| Credential in source code | Credentials resolved at runtime via `get_api_credential()`, never in generated code |
| Credential in logs | Strip auth headers from error messages |
| Malicious spec | Validate spec against OpenAPI JSON Schema before parsing |
| Unbounded requests | Generated tools use `httpx.AsyncClient(timeout=30.0)` |
| Rate limit bypass | Add configurable rate limit decorator to generated tools |
| Large response DoS | Cap response body to 10 MB |

### 4.3 Credential Storage Schema

```sql
CREATE TABLE api_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,            -- e.g., "stripe_api_key"
    encrypted_value TEXT NOT NULL, -- AES-256 encrypted
    auth_scheme TEXT NOT NULL,     -- "api_key", "bearer", "basic", "oauth2"
    metadata JSONB,               -- {header_name, prefix, scopes, etc.}
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, name)
);

ALTER TABLE api_credentials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own credentials" ON api_credentials
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service role full access" ON api_credentials
    FOR ALL USING (auth.role() = 'service_role');
```

---

## Part 5: Generated Tool Lifecycle

### 5.1 Creation Flow

1. Agent calls `connect_api(spec_url="https://api.example.com/openapi.json", api_name="example")`
2. Parser fetches + validates spec → extracts endpoints
3. Agent (or user) selects relevant endpoints (max 10 per connection)
4. Code generator produces Python functions for each endpoint
5. Validator runs `ast.parse()` + generated pytest tests
6. On success: register via `custom_skills_service.create_skill()` per endpoint
7. Add to `tool_registry` for workflow access
8. Return tool names and usage instructions to the agent

### 5.2 Self-Healing on API Changes

When a generated tool fails with a schema mismatch or 4xx error:

1. Tool catches the error and logs it
2. If error count > 3 in 24h: flag the API connection as "stale"
3. Agent (or background job) re-fetches the spec
4. Diff old vs new endpoints
5. Regenerate + revalidate changed tools
6. Replace registered tools atomically

### 5.3 Deletion Flow

1. Agent calls `disconnect_api(api_name="example")`
2. Find all skills with `metadata.api_connection == "example"`
3. Deactivate skills via `custom_skills_service.deactivate_skill()`
4. Remove from tool_registry
5. Optionally delete stored credential

---

## Part 6: Implementation Phases

### Phase 1: API Parser + Core Generator
1. `app/skills/api_parser.py` — OpenAPI 3.x parser with $ref resolution
2. `app/skills/api_codegen.py` — Python code generator for endpoints
3. `app/skills/api_auth.py` — Runtime credential resolution
4. Tests for parser (sample OpenAPI specs) and generator (snapshot tests)
5. Database migration: `api_credentials` table

### Phase 2: ADK Tool + Agent Integration
1. `app/agents/tools/api_connector.py` — `connect_api`, `list_api_connections`, `disconnect_api`
2. Wire into ExecutiveAgent tools
3. Register in tool_registry for workflow access
4. Credential management tools (store, list, delete)

### Phase 3: Validation + Security
1. SSRF protection (URL validation)
2. Spec sanitization (prevent code injection)
3. Rate limit decorator for generated tools
4. Credential encryption at rest
5. Generated test execution in subprocess sandbox

### Phase 4: Self-Healing + Observability
1. API health monitoring (track error rates per connection)
2. Stale spec detection + auto-regeneration
3. Usage tracking per generated tool
4. Dashboard widget: API connections status, tool usage, error rates

---

## Part 7: Integration Points

```
connect_api (ADK Tool)
  → api_parser.py (NEW)         → OpenAPI spec extraction
  → api_codegen.py (NEW)        → Python function generation
  → api_auth.py (NEW)           → Credential injection at runtime
  → skill_builder.py (EXISTING) → ast.parse + pytest validation
  → custom_skills_service (EXISTING) → Supabase persistence
  → registry.py (EXISTING)      → Tool registration for workflows
  → loader.py (EXISTING)        → Dynamic hot-loading
  → agent_skills.py (EXISTING)  → Agent-aware access control
```

---

## Part 8: Example Usage

### User Flow
```
User: "Connect to the HubSpot API. Here's the spec: https://api.hubspot.com/api-catalog-public/v1/apis"

Agent: I'll connect to the HubSpot API. First, I need your API key.
       Please go to Configuration → API Credentials and add your HubSpot key
       with the name "hubspot_api_key".

User: "Done."

Agent: [calls connect_api(spec_url="...", api_name="hubspot", secret_name="hubspot_api_key")]

Agent: I've connected to the HubSpot API and created 8 tools:
       1. hubspot_list_contacts — List contacts with filtering
       2. hubspot_get_contact — Get contact by ID
       3. hubspot_create_contact — Create a new contact
       4. hubspot_list_deals — List deals with pipeline filtering
       5. hubspot_get_deal — Get deal by ID
       6. hubspot_create_deal — Create a new deal
       7. hubspot_list_companies — List companies
       8. hubspot_search_contacts — Search contacts by query

       All tools are now available to the Sales and Marketing agents.
       Try: "List all contacts from HubSpot"
```

---

## Part 9: Success Metrics

| Metric | Target |
|--------|--------|
| Spec parse success rate | > 90% for valid OpenAPI 3.x specs |
| Generated tool validation pass rate | > 95% |
| Time from spec URL to usable tools | < 30 seconds for 10 endpoints |
| Generated tool runtime error rate | < 5% |
| Self-healing success rate | > 80% (auto-fix stale tools) |
| Supported auth schemes | 4+ (API key, bearer, basic, OAuth2 CC) |
