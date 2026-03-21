# Stack Research

**Domain:** AI-first admin panel for multi-agent executive system
**Researched:** 2026-03-21
**Confidence:** HIGH (all additions verified against PyPI, npm, and official docs)

---

## Context: Additions Only

This is a subsequent-milestone research document. The existing stack (FastAPI, Google ADK,
Gemini, Next.js 16, React 19, Tailwind CSS 4, Supabase, Redis, slowapi, fetchEventSource,
Framer Motion, Lucide, Sonner) is validated and must NOT be replaced. This document covers
only what is NEW for the admin panel.

---

## New Backend Dependencies (Python)

### Core New Additions

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `cryptography` (Fernet) | `>=46.0.3` (already in pyproject.toml) | API key encryption for `admin_integrations` table | Already a direct dependency. `Fernet` from `cryptography.fernet` provides AES-128-CBC + HMAC-SHA256 with `MultiFernet` for zero-downtime key rotation. No new package needed — just import and use. |
| `httpx` | `~=0.28.1` | Async HTTP client for health monitoring loop and external API proxy | FastAPI's recommended async client (used in FastAPI's own test utilities). Supports `AsyncClient` with timeouts and `asyncio.gather()` for concurrent health checks. Superior to `aiohttp` for this use case because it has a `requests`-compatible API, HTTP/2 support, and first-class FastAPI integration. |
| `posthog` | `~=7.9.12` | Server-side PostHog client for the PostHog integration proxy tools | Official Python SDK for PostHog. Enables `capture()`, feature flag queries, and insight reads server-side without exposing the API key to the frontend. |
| `sentry-sdk` | `~=2.53.0` | Sentry API client for the Sentry integration proxy tools | Official Sentry Python SDK. The admin agent's Sentry tools (`sentry_get_issues`, `sentry_resolve_issue`) call Sentry's REST API via `httpx` directly (not the SDK's error-capture path) — the SDK is used only for structured API access patterns and its typed interfaces. |
| `PyGithub` | `~=2.8.1` | GitHub REST API client for the GitHub integration proxy tools | Typed wrapper around GitHub API v3. Covers `github_list_prs` and `github_get_pr_status` tools cleanly. Alternative is raw `httpx` calls but PyGithub provides typed models and handles pagination. |

### What NOT to Add (Backend)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `alembic` | Project uses Supabase migrations as schema source of truth (96 migrations vs 1 stale Alembic file). Adding Alembic risks schema drift and dual-migration confusion. | Supabase CLI (`supabase db push`) for all schema changes |
| `celery` / `dramatiq` / `rq` | Heavy task-queue infrastructure for a scheduled health check that Cloud Scheduler already handles via `POST /admin/monitoring/run-check`. Over-engineering for a 60s polling loop. | Cloud Scheduler triggering FastAPI endpoint (existing pattern in `scheduled_endpoints.py`) |
| `aiohttp` | httpx already covers async HTTP and has better FastAPI ergonomics. Two async HTTP libraries in one project creates confusion. | `httpx` AsyncClient |
| `websockets` / `python-socketio` | PROJECT.md explicitly scopes out real-time WebSocket monitoring — SSE and polling are sufficient for admin use cases. | FastAPI SSE + `@microsoft/fetch-event-source` (existing pattern) |
| `jwt` (standalone) | `PyJWT>=2.8.0` is already a direct dependency in pyproject.toml. | Existing `PyJWT` |
| `coderabbit` SDK | No official Python SDK exists. CodeRabbit exposes a REST API — use `httpx` directly with the auth token. | `httpx` AsyncClient with the CodeRabbit API token |

---

## New Frontend Dependencies (npm)

### Core New Additions

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@tanstack/react-table` | `^8.21.3` | Headless table engine for user management and audit log data grids | Use for `/admin/users`, `/admin/audit-log`, and `/admin/approvals` — any table with server-side sorting, filtering, and pagination. Pairs with existing Tailwind + Lucide for rendering. React 19 compatible. |
| `recharts` | `^3.8.0` | Chart library for analytics dashboards and monitoring sparklines | Use for `/admin/analytics` (DAU/MAU charts, agent effectiveness, retention) and `/admin/monitoring` (response time sparklines, 24h trend lines). Version 3.x has native React 19 support without `react-is` workarounds needed in 2.x. |

### What NOT to Add (Frontend)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `shadcn/ui` as an installed package | shadcn/ui is a copy-paste component system, not a versioned npm package. The project already has Tailwind CSS 4 + Lucide + Framer Motion + Sonner — adding shadcn adds an initialization layer that would conflict with the existing design system and its own Tailwind config approach. | Build admin table/card/filter components using existing Tailwind CSS 4 + Lucide primitives. Reference shadcn patterns for implementation but do not install it. |
| `tremor` | Acquired by Vercel in Jan 2025 and still in transition. Built on Recharts anyway — adds an abstraction layer with less flexibility than direct Recharts usage. The project already has Tailwind CSS 4 which Tremor would partially override. | `recharts` directly |
| `@radix-ui/react-*` (standalone) | The project doesn't use Radix. Admin panel should use existing patterns: Framer Motion for animation, Sonner for toasts, Lucide for icons. Introducing Radix piecemeal creates an inconsistent primitive layer. | Existing Framer Motion + Tailwind CSS 4 for modals/sheets/overlays |
| `react-query` / `@tanstack/react-query` | Admin dashboard data can be fetched with standard `useEffect` + `fetch` + Supabase client. Adding a full data-fetching layer for what amounts to a founder-only panel is over-engineering. | Supabase client + standard fetch for admin API calls |
| `ag-grid-react` / `react-data-grid` | Heavy commercial data grid overkill for an admin panel with ~hundreds of rows (not millions). TanStack Table is headless and lighter. | `@tanstack/react-table` |
| `chart.js` / `victory` | Less ergonomic with React 19 than Recharts. recharts 3.x is the standard for React/Next.js admin dashboards. | `recharts` |
| `react-hook-form` | Admin forms (integration config, agent config editor) are simple enough for controlled components. Adding a form library for a handful of admin forms is unnecessary complexity. | Native React controlled inputs with Tailwind CSS 4 |
| WebSocket client library | Out of scope per PROJECT.md. SSE + polling is the specified approach for admin monitoring. | Existing `@microsoft/fetch-event-source` pattern |

---

## Fernet Encryption: No New Package Needed

`cryptography>=46.0.3` is already a direct dependency in `pyproject.toml`. The Fernet API
is stable across all recent versions:

```python
from cryptography.fernet import Fernet, MultiFernet

# Generate a key (do once, store in ADMIN_ENCRYPTION_KEY env var)
key = Fernet.generate_key()

# Encrypt an API key before storing
f = Fernet(key)
encrypted = f.encrypt(b"sk-live-abc123...")

# Decrypt when needed for outbound API calls
decrypted = f.decrypt(encrypted)

# Key rotation: MultiFernet tries each key in order, encrypts with first
f_multi = MultiFernet([Fernet(new_key), Fernet(old_key)])
rotated_token = f_multi.rotate(existing_token)
```

**Key rotation pattern:** Store `ADMIN_ENCRYPTION_KEY` in env/Secret Manager. For rotation,
add `ADMIN_ENCRYPTION_KEY_PREVIOUS`. Migration script calls `MultiFernet.rotate()` on each
stored token, then removes the old key env var.

---

## Admin Agent Pattern (Google ADK)

No new ADK-specific packages are needed. The admin agent follows the same pattern as existing
specialized agents. Key notes from ADK documentation:

- Assign plain Python async functions to `tools=[]` — ADK auto-wraps them as `FunctionTool`
- Function docstrings become the tool description the LLM sees — write them carefully
- Type hints in function signatures are used to generate the tool's JSON schema
- The admin agent gets the same `get_model()` / `get_fallback_model()` from `app/agents/shared.py`

```python
# Pattern: admin tool function
async def suspend_user(user_id: str, reason: str) -> dict:
    """Suspend a user account, disabling their access to all services.

    Args:
        user_id: UUID of the user to suspend.
        reason: Reason for suspension (logged to audit trail).

    Returns:
        Dict with success status and suspended user details.
    """
    # Check autonomy level before executing
    # Perform action, log to admin_audit_log
    ...

# Pattern: agent construction (consistent with existing agents)
admin_agent = Agent(
    name="AdminAgent",
    model=get_model(),
    tools=[suspend_user, unsuspend_user, list_users, ...],
    instruction=ADMIN_SYSTEM_PROMPT,
)
```

---

## Health Monitoring: httpx + asyncio.gather

The monitoring loop calls multiple endpoints concurrently. httpx `AsyncClient` with
`asyncio.gather()` is the right pattern — no additional library needed:

```python
import asyncio
import httpx

async def run_health_checks(endpoints: list[str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [check_endpoint(client, ep) for ep in endpoints]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

This pattern is already in use in parts of the codebase for parallel async operations.

---

## SSE Streaming: No Changes Needed

Admin chat follows the exact same pattern as `useAgentChat`:
- Backend: FastAPI `StreamingResponse` with `text/event-stream` content type
- Frontend: `@microsoft/fetch-event-source` (already installed at `^2.0.1`)
- Hook: New `useAdminChat` hook modeled after existing `useAgentChat.ts`

The only admin-specific addition is the `X-Impersonate-User-Id` header passthrough for
impersonation mode — no new library needed.

---

## charting: recharts 3.x vs 2.x Decision

Use recharts `^3.8.0` (not 2.x). Rationale:
- React 19 native support without the `react-is` override that 2.x requires
- `3.8.0` is the current stable release (released March 2025)
- TypeScript generics for `data` and `dataKey` props added in 3.x — prevents runtime errors
  in admin dashboard charts
- The existing `package.json` does not have recharts installed at all, so there is no
  migration cost

**recharts 3.x breaking changes to be aware of:**
- `activeIndex` prop removed from `Scatter`/`Bar`/`Pie` — use `Tooltip` instead
- No `CategoricalChartState` passed through cloned props
- Z-index controlled by render order (SVG-native), not `zIndex` prop

---

## Data Tables: @tanstack/react-table v8 Pattern

The admin panel needs server-side pagination (users table can be large). TanStack Table
v8 supports this with the `manualPagination` option:

```tsx
const table = useReactTable({
  data,
  columns,
  manualPagination: true,
  pageCount: Math.ceil(total / pageSize),
  state: { pagination },
  onPaginationChange: setPagination,
  getCoreRowModel: getCoreRowModel(),
});
```

This is headless — all styling is Tailwind CSS 4, consistent with the rest of the app.
No new CSS dependencies.

---

## Installation

```bash
# Python — add to pyproject.toml dependencies
# cryptography is already present (no change needed)
uv add "httpx~=0.28.1"
uv add "posthog~=7.9.12"
uv add "sentry-sdk~=2.53.0"
uv add "PyGithub~=2.8.1"

# Frontend — add to frontend/package.json
cd frontend
npm install recharts@^3.8.0
npm install @tanstack/react-table@^8.21.3
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `httpx` for health monitoring | `aiohttp` | Only if project was already using aiohttp throughout. httpx is strictly better here given FastAPI integration. |
| `recharts` 3.x | Tremor | If you want a full pre-styled dashboard component system with no customization. Tremor is built on recharts anyway and is less flexible. |
| `@tanstack/react-table` | `ag-grid-react` | If the admin panel needed Excel-like inline editing, virtual scrolling for 100k+ rows, or built-in enterprise features. Not the case here. |
| `PyGithub` for GitHub tools | Raw `httpx` calls | If GitHub scope expands beyond PRs/checks to webhooks, Actions, or GitHub Apps. PyGithub 2.x covers the needed subset cleanly. |
| Fernet (existing `cryptography`) | AWS KMS / GCP Cloud KMS | If regulatory compliance requires HSM-backed encryption. For a founder admin panel, application-layer Fernet with a Secret Manager key is the right tradeoff. |
| Cloud Scheduler + FastAPI endpoint | Celery beat / APScheduler | If the project needed dozens of scheduled tasks with complex dependencies. Single health check loop doesn't justify an async task queue. |

---

## Version Compatibility Matrix

| Package | Requires | Notes |
|---------|----------|-------|
| `recharts@^3.8.0` | `react@>=16.8`, TypeScript 5.x, Node 18+ | React 19 supported natively in 3.x |
| `@tanstack/react-table@^8.21.3` | `react@>=16.8` | React 19 compatible; React Compiler compatibility not yet guaranteed — avoid `"use client"` memo optimizations on table components |
| `httpx~=0.28.1` | Python 3.8+ | Compatible with Python 3.10-3.13 (project range) |
| `posthog~=7.9.12` | Python 3.10+ (v7.x dropped 3.9) | Matches project's `>=3.10,<3.14` range |
| `sentry-sdk~=2.53.0` | Python 3.8+ | FastAPI integration available but not needed for admin proxy pattern — we use its REST client patterns, not its error capture |
| `PyGithub~=2.8.1` | Python 3.8+ | Async support via `github.Github` is synchronous only — wrap in `asyncio.to_thread()` for FastAPI async handlers |

**Important:** PyGithub is synchronous. The admin agent tools that call GitHub must use
`await asyncio.to_thread(github_call)` to avoid blocking the FastAPI event loop.

---

## Sources

- PyPI: httpx 0.28.1 — https://pypi.org/project/httpx/
- PyPI: posthog 7.9.12 — https://pypi.org/project/posthog/
- PyPI: sentry-sdk 2.53.0 — https://pypi.org/project/sentry-sdk/
- PyPI: PyGithub 2.8.1 — https://pypi.org/project/PyGithub/
- recharts v3.8.0 release — https://github.com/recharts/recharts/releases (March 2025)
- recharts 3.0 migration guide — https://github.com/recharts/recharts/wiki/3.0-migration-guide
- @tanstack/react-table 8.21.3 — https://tanstack.com/table/v8/docs/installation
- cryptography 46.0.x Fernet docs — https://cryptography.io/en/stable/fernet/ (HIGH confidence)
- Google ADK FunctionTool patterns — https://google.github.io/adk-docs/tools-custom/function-tools/ (HIGH confidence)
- shadcn/ui Tailwind v4 + React 19 — https://ui.shadcn.com/docs/tailwind-v4 (MEDIUM confidence, verifies recharts/Tailwind v4 interplay)
- httpx FastAPI async patterns — https://www.python-httpx.org/async/ (HIGH confidence)

---

*Stack research for: Pikar-AI v3.0 Admin Panel*
*Researched: 2026-03-21*
