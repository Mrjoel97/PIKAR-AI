# Phase 12: Agent Config + Feature Flags — Research

**Researched:** 2026-03-23
**Domain:** Agent instruction management, feature flag storage, injection validation, config versioning
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-01 | Admin can edit agent instructions with before/after diff display | `admin_config_history` table (Phase 7), Python `difflib.unified_diff` stdlib, new `admin_agent_configs` table for live instructions |
| CONF-02 | System tracks config version history with one-click rollback | `admin_config_history` already exists; needs `config_key` semantics defined for agent instructions vs flags |
| CONF-03 | Admin can toggle feature flags from UI, takes effect within 60 seconds | New `admin_feature_flags` table + Redis cache with 60s TTL; feature_flags.py currently reads env vars — must extend to DB source |
| CONF-04 | Admin can configure per-action autonomy tiers (auto/confirm/blocked) | `admin_agent_permissions` table already exists and is seeded; needs UI + tools to read/write it |
| CONF-05 | Admin can manage MCP server and API endpoint configurations | `admin_integrations` pattern reused; new section in config page for MCP endpoints |
| SKIL-07 | AdminAgent can assess impact of agent config changes — which workflows depend on target agent | `WorkflowRegistry._metadata` has `"module"` field; agent-to-workflow map derivable at runtime from `category` metadata |
| SKIL-08 | AdminAgent can recommend rollback when config change correlates with degraded metrics | `admin_agent_stats_daily` (success_rate, avg_duration_ms) + `admin_config_history.created_at` give pre/post windows |
</phase_requirements>

---

## Summary

Phase 12 adds the configuration management domain to the Admin Panel. It is the only phase that mutates the live behavior of the 10 specialized agents: it edits their instruction strings, toggles feature flags, and reconfigures autonomy tiers. The primary engineering risks are (1) prompt injection via the instruction editor, (2) config race conditions between UI updates and the running ADK agents, and (3) the 60-second feature flag propagation requirement.

The Phase 7 database migration already created `admin_config_history` as a generic version-history table. Phase 12 must add two new tables — `admin_agent_configs` (current live instructions per agent) and `admin_feature_flags` (flag key/value/enabled store) — and extend the existing feature_flags.py service to read from DB with Redis caching rather than purely from environment variables. The existing `admin_agent_permissions` table already stores autonomy tiers; Phase 12 adds the UI and tools to let the admin edit them.

The AdminAgent skills (SKIL-07 and SKIL-08) are pure instruction-level reasoning patterns injected into the agent's system prompt, following the SKIL-01/SKIL-02 pattern from Phase 11. They require two new auto-tier tools: `assess_config_impact` (queries WorkflowRegistry for agent dependencies) and `recommend_config_rollback` (compares pre/post change windows in `admin_agent_stats_daily`).

**Primary recommendation:** Store live agent instructions in a new `admin_agent_configs` table (one row per agent name); store feature flags in `admin_feature_flags`; use Redis with 60s TTL as the read path for flags; use `difflib.unified_diff` (stdlib) for the diff display; use Python string allowlist + regex for injection validation.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `difflib` | stdlib | Unified diff generation for before/after instruction display | No new dependency; `difflib.unified_diff` produces standard unified diff format |
| Python `re` | stdlib | Prompt injection validation (detect system prompt override patterns) | No new dependency; sufficient for pattern-based allowlist/blocklist |
| `supabase-py` | existing | CRUD on `admin_agent_configs`, `admin_feature_flags`, `admin_agent_permissions` | Already in use for all admin tables |
| `aioredis` / Redis | existing | 60s TTL cache for feature flags; circuit breaker already in `app/services/cache.py` | Already in use; circuit-breaker-safe pattern established in Phase 7 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `WorkflowRegistry` | internal | Derive which workflows use a given agent (SKIL-07) | agent-to-workflow impact assessment at runtime |
| `admin_agent_stats_daily` | internal table | Pre/post performance comparison for rollback recommendation (SKIL-08) | already populated by Phase 10 aggregator |
| `admin_config_history` | Phase 7 table | Append-only version log for all config changes | every save writes a row here |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `difflib.unified_diff` (stdlib) | `diff-match-patch` npm lib, server-side | stdlib requires no dependency; unified diff is readable in a textarea; rich character-level diff deferred to future polish |
| DB-backed feature flags | LaunchDarkly, Unleash | External services add dependency cost; at this scale a simple Supabase table + Redis TTL is sufficient and keeps all state in-house |
| Redis 60s TTL for flags | Direct DB query per request | Redis is already wired with circuit breaker; polling every request would add DB load |

**Installation:** No new Python dependencies required. All necessary libraries are stdlib or already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── agents/admin/tools/
│   └── config.py              # 5 new AdminAgent tools (Phase 12)
├── routers/admin/
│   └── config.py              # REST endpoints: agent configs, feature flags, permissions, MCP endpoints
├── services/
│   └── agent_config_service.py  # Config read/write, injection validation, diff generation
supabase/migrations/
└── 202603XX000000_agent_config_feature_flags.sql  # 2 new tables + permissions seed rows
frontend/src/
├── app/(admin)/config/
│   └── page.tsx               # Config management page (tabbed: Instructions / Feature Flags / Autonomy / MCP)
└── components/admin/config/
    ├── AgentConfigEditor.tsx  # Instruction textarea + diff panel
    ├── VersionHistory.tsx     # Version list + restore button
    ├── FeatureFlagRow.tsx     # Toggle row for each flag
    └── AutonomyTable.tsx      # Table of admin_agent_permissions rows with tier selectors
```

### Pattern 1: Agent Config Table (new `admin_agent_configs`)

**What:** One row per agent name. `current_instructions TEXT` is the live value injected at agent creation. Every write also appends a row to `admin_config_history`.

**When to use:** All reads/writes to agent instructions go through this table, never directly to Python source files.

```sql
-- Source: Phase 7 migration pattern (admin_config_history already exists)
CREATE TABLE IF NOT EXISTS admin_agent_configs (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name        text NOT NULL UNIQUE,
    current_instructions text NOT NULL,
    version           integer NOT NULL DEFAULT 1,
    updated_by        uuid REFERENCES auth.users(id),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    created_at        timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE admin_agent_configs ENABLE ROW LEVEL SECURITY;
```

**config_history semantics for agent instructions:**
- `config_type = 'agent_instruction'`
- `config_key = <agent_name>` (e.g. `'financial'`, `'content'`)
- `previous_value = {"instructions": "<old text>", "version": N}`
- `new_value = {"instructions": "<new text>", "version": N+1}`

### Pattern 2: Feature Flag Table (new `admin_feature_flags`)

**What:** One row per flag key. The `is_enabled` boolean is the source of truth. Redis caches it with 60s TTL. The existing `feature_flags.py` is extended with a `get_flag(key)` async function that reads Redis first, then DB.

**When to use:** All runtime feature flag checks call `get_flag(key)` — never `os.getenv()` directly for flags that need to be toggleable from the admin panel.

```sql
CREATE TABLE IF NOT EXISTS admin_feature_flags (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_key    text NOT NULL UNIQUE,
    is_enabled  boolean NOT NULL DEFAULT false,
    description text,
    updated_by  uuid REFERENCES auth.users(id),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    created_at  timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE admin_feature_flags ENABLE ROW LEVEL SECURITY;
```

**Redis cache key pattern:** `admin:feature_flag:{flag_key}` with 60s TTL. On toggle: write DB, then `SETEX` Redis key. On read: `GET` Redis → on miss fetch DB + cache. Circuit breaker in `app/services/cache.py` means flag reads fall back to DB on Redis downtime.

### Pattern 3: Diff Generation (backend)

**What:** The API endpoint for saving an agent config change returns the unified diff in the response so the frontend can display it before the admin confirms.

```python
# Source: Python stdlib difflib — no external dependency
import difflib

def generate_instruction_diff(old: str, new: str) -> str:
    """Return unified diff of instruction changes."""
    lines_old = old.splitlines(keepends=True)
    lines_new = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        lines_old, lines_new,
        fromfile="current",
        tofile="proposed",
        lineterm="",
    )
    return "".join(diff)
```

The frontend calls `POST /admin/config/agents/{agent_name}/preview-diff` with `{proposed_instructions}` and receives `{diff: "..."}` before the admin clicks Confirm. The actual write only happens on `POST /admin/config/agents/{agent_name}` with a `confirmation_token` (confirm-tier autonomy).

### Pattern 4: Injection Validation

**What:** Before any instruction string reaches `admin_config_history` or `admin_agent_configs`, validate it through a blocklist regex + length cap.

**Why:** Admin panel itself could be a vector if an attacker gains admin access or if the admin pastes content from an untrusted source. Validation prevents "IGNORE ALL PREVIOUS INSTRUCTIONS" style content from being stored and later injected into the Gemini prompt.

```python
# Source: project security pattern (bandit scanning in pre-commit)
import re

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"disregard\s+(?:your\s+)?(?:previous|prior|earlier)", re.IGNORECASE),
    re.compile(r"your\s+new\s+instructions?\s+are", re.IGNORECASE),
]
_MAX_INSTRUCTION_LENGTH = 32_000  # chars; Gemini 2.5 Pro context is large but we cap for sanity

def validate_instruction_content(text: str) -> list[str]:
    """Return list of violation descriptions. Empty list = valid."""
    violations = []
    if len(text) > _MAX_INSTRUCTION_LENGTH:
        violations.append(f"Instruction exceeds {_MAX_INSTRUCTION_LENGTH} character limit")
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            violations.append(f"Potential injection pattern detected: '{pattern.pattern}'")
    return violations
```

Return HTTP 422 with the violations list if any are found. This is the validation gate on `POST /admin/config/agents/{agent_name}` — never write without passing validation.

### Pattern 5: AdminAgent Config Tools

**What:** 5 new tools in `app/agents/admin/tools/config.py` following the exact pattern from `analytics.py` and `integrations.py`.

| Tool | Tier | Description |
|------|------|-------------|
| `get_agent_config` | auto | Read current instructions + version for an agent |
| `update_agent_config` | confirm | Write new instructions (validation included in tool) |
| `get_config_history` | auto | List version history for an agent or all agents |
| `rollback_agent_config` | confirm | Restore a previous version by history row ID |
| `get_feature_flags` | auto | List all feature flags with current enabled state |
| `toggle_feature_flag` | confirm | Enable or disable a feature flag by key |
| `get_autonomy_permissions` | auto | List all admin_agent_permissions rows |
| `update_autonomy_permission` | confirm | Change autonomy_level for an action |
| `assess_config_impact` | auto | SKIL-07: list workflows that use target agent |
| `recommend_config_rollback` | auto | SKIL-08: compare pre/post performance windows |

That is 10 tools, split across 2 files if needed for module size. The existing pattern is all tools in one file per domain. Given the breadth, split into `config.py` (8 CRUD tools) and keep skills as instruction-level reasoning (SKIL-07/08 require `assess_config_impact` and `recommend_config_rollback` as lightweight tools).

### Pattern 6: 60-Second Feature Flag Propagation

**What:** New sessions read flags from Redis (60s TTL). This means at most 60 seconds of stale flag state for new sessions. In-flight sessions are NOT affected — they do not re-read flags mid-session. This is the intended behavior given agents are stateless between ADK runner calls.

**How confirmed:** The existing `AdminAgent` uses `Per-request ADK Runner with InMemorySessionService` (Phase 7 decision). Instructions are passed at agent creation time. To pick up a new instruction, the next request (new Runner instance) will call the updated instruction from DB. No hot-reload mechanism is needed.

### Anti-Patterns to Avoid

- **Writing instructions directly to Python files** at runtime — never mutate `app/agents/*/agent.py` on disk. Store instructions in DB, inject at runner creation time.
- **Skipping validation on rollback** — a rollback restores a previous value; still run injection validation on the restored content (though it was previously approved, defence-in-depth).
- **Exposing raw diff to untrusted users** — diff endpoint is admin-only via `require_admin`.
- **Storing feature flag state in environment variables** — env vars require redeploy; the whole point of Phase 12 flags is runtime toggleability.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diff algorithm | Custom character diff | Python `difflib.unified_diff` | Edge cases in Unicode, empty lines, newline handling; stdlib is battle-tested |
| Injection detection | Fine-grained NLP | Regex blocklist | NLP adds model dependency and latency; regex is fast and auditable; high-confidence patterns are sufficient |
| Feature flag SDK | Full LaunchDarkly-style targeting (user segments, gradual rollouts) | Simple boolean Supabase table + Redis TTL | Over-engineering; this admin panel is single-admin, not multi-tenant; targeting rules deferred to future |
| Optimistic lock version conflict handling | Custom CAS loop | Supabase upsert with version check + 409 on conflict | Supabase upsert with `on_conflict` is atomic at DB level |

---

## Common Pitfalls

### Pitfall 1: Agent Instructions Not Picked Up at Runtime

**What goes wrong:** Admin saves new instructions but running agent still uses old instructions.
**Why it happens:** ADK `admin_agent` singleton in `agent.py` is initialized at import time with the hardcoded `ADMIN_AGENT_INSTRUCTION` string. DB instructions won't be visible until the next request that creates a new Runner.
**How to avoid:** Change the runner creation pattern to fetch live instructions from DB (or Redis-cached) at `AdminAgent` instantiation time, not at module import. Use the `create_admin_agent()` factory (already exists) and pass instructions as a parameter fetched from DB. Per-request runner already confirmed in Phase 7 decisions — this is the right hook.
**Warning signs:** After saving instructions in UI, the agent still exhibits old behavior in the next message.

### Pitfall 2: Config History `config_key` Collision

**What goes wrong:** `admin_config_history` is a generic table used by all config types. Two operations on the same `(config_type, config_key)` pair could confuse version ordering if created_at has second-level precision.
**Why it happens:** Phase 7 created `admin_config_history` without a `version` column; ordering relies on `created_at`.
**How to avoid:** Add `version integer` to `admin_agent_configs` (owned table), not to `admin_config_history`. The history table is append-only; order by `created_at DESC` to get "most recent first" version list. Use microsecond-precision `timestamptz` (Postgres default) — sub-millisecond collision is negligible for human admin actions.

### Pitfall 3: Feature Flag 60-Second Window Misunderstanding

**What goes wrong:** Admin toggles flag, expects immediate effect for current active user sessions.
**Why it happens:** Redis TTL means in-flight sessions still read the old value.
**How to avoid:** Document in UI: "Changes take effect for new sessions within 60 seconds." Do not promise instant propagation to active sessions. If truly instant is needed later, consider Redis pub/sub — out of scope for Phase 12.

### Pitfall 4: Autonomy Tier Table Divergence

**What goes wrong:** Admin updates an autonomy tier via UI, but the tool code still has the old default seeded by Phase 7 migration. The `check_autonomy()` function in `_autonomy.py` queries the DB — so the live tier IS correct. However, the seed migration has `'update_config': 'confirm'` — Phase 12 seeds NEW config-domain tools (get_agent_config, update_agent_config, etc.) with appropriate defaults.
**Why it happens:** Forgetting to seed new tools into `admin_agent_permissions` when they are added.
**How to avoid:** Every new tool in `config.py` MUST have a corresponding `INSERT` into `admin_agent_permissions` in the Phase 12 migration. Check against the Phase 7 and Phase 10 seed patterns.

### Pitfall 5: Prompt Injection via Rollback

**What goes wrong:** A previously approved instruction contained a subtle injection; admin rolls back to it, re-activating the payload.
**Why it happens:** Validation only ran at time of original save; rollback skips validation.
**How to avoid:** Run `validate_instruction_content()` on the rolled-back text before writing. Return 422 if it now violates patterns (edge case: patterns updated since original save).

---

## Code Examples

### Unified Diff Generation

```python
# Source: Python stdlib difflib documentation
import difflib

def generate_instruction_diff(old: str, new: str) -> str:
    lines_old = old.splitlines(keepends=True)
    lines_new = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        lines_old, lines_new,
        fromfile="current",
        tofile="proposed",
        lineterm="",
    )
    return "".join(diff)
```

### Feature Flag Read with Redis Cache

```python
# Source: Established Redis circuit-breaker pattern from app/services/cache.py
import json
import logging
from app.services.cache import get_cache_client
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)
_FLAG_TTL = 60  # seconds — satisfies CONF-03 requirement

async def get_flag(key: str, default: bool = False) -> bool:
    """Read feature flag from Redis (60s TTL) with DB fallback."""
    cache_key = f"admin:feature_flag:{key}"
    try:
        cache = await get_cache_client()
        if cache:
            cached = await cache.get(cache_key)
            if cached is not None:
                return json.loads(cached)
    except Exception:
        logger.warning("Redis unavailable for flag %s, falling back to DB", key)

    # DB fallback (also used to populate cache on miss)
    client = get_service_client()
    res = (
        client.table("admin_feature_flags")
        .select("is_enabled")
        .eq("flag_key", key)
        .limit(1)
        .execute()
    )
    if not res.data:
        return default
    enabled = res.data[0].get("is_enabled", default)

    # Re-populate cache
    try:
        cache = await get_cache_client()
        if cache:
            await cache.setex(cache_key, _FLAG_TTL, json.dumps(enabled))
    except Exception:
        pass  # non-fatal — fail open

    return enabled
```

### Autonomy Tier Update (confirm-tier tool)

```python
# Source: _autonomy.py pattern + integrations.py update pattern
async def update_autonomy_permission(
    action_name: str,
    new_level: str,
    confirmation_token: str | None = None,
) -> dict:
    """Change autonomy tier for an admin action. Confirm-tier."""
    gate = await _check_autonomy("update_autonomy_permission")
    if gate is not None and confirmation_token is None:
        return gate
    # confirmation_token provided = admin confirmed; proceed
    if new_level not in ("auto", "confirm", "blocked"):
        return {"error": f"Invalid autonomy level '{new_level}'"}
    client = get_service_client()
    client.table("admin_agent_permissions").update(
        {"autonomy_level": new_level}
    ).eq("action_name", action_name).execute()
    return {"action_name": action_name, "autonomy_level": new_level, "status": "updated"}
```

### SKIL-07: Workflow Impact Assessment Tool

```python
# Source: WorkflowRegistry pattern from app/workflows/registry.py
async def assess_config_impact(agent_name: str) -> dict:
    """SKIL-07: List workflows that use the target agent. Auto-tier."""
    gate = await _check_autonomy("assess_config_impact")
    if gate is not None:
        return gate

    from app.workflows.registry import get_workflow_registry
    registry = get_workflow_registry()
    # agent_name maps to workflow category (financial, content, marketing, etc.)
    # Registry metadata has "module" — derive agent domain from category match
    agent_categories = {
        "financial": "financial", "content": "content", "marketing": "marketing",
        "strategic": "goals", "sales": "sales", "hr": "hr",
        "compliance": "compliance", "operations": "initiative",
        "data": "evaluation", "customer_support": "knowledge",
    }
    category = agent_categories.get(agent_name.lower())
    workflows_using_agent = []
    if category:
        workflows_using_agent = registry.list_by_category(category)

    # Also query agent_telemetry for call volume (7-day window)
    client = get_service_client()
    telem = (
        client.table("agent_telemetry")
        .select("agent_name, status")
        .eq("agent_name", agent_name)
        .gte("created_at", "now() - interval '7 days'")
        .execute()
    )
    call_count = len(telem.data or [])

    return {
        "agent_name": agent_name,
        "workflows_using_agent": workflows_using_agent,
        "workflow_count": len(workflows_using_agent),
        "calls_last_7_days": call_count,
        "risk_assessment": (
            "HIGH" if call_count > 100 else
            "MEDIUM" if call_count > 20 else "LOW"
        ),
    }
```

### SKIL-08: Rollback Recommendation Tool

```python
# Source: admin_agent_stats_daily pattern from Phase 10
async def recommend_config_rollback(agent_name: str) -> dict:
    """SKIL-08: Compare pre/post-change performance. Auto-tier."""
    gate = await _check_autonomy("recommend_config_rollback")
    if gate is not None:
        return gate

    client = get_service_client()
    # Find last config change for this agent
    hist = (
        client.table("admin_config_history")
        .select("created_at, new_value, previous_value, id")
        .eq("config_type", "agent_instruction")
        .eq("config_key", agent_name)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not hist.data:
        return {"recommendation": "no_config_change_found", "agent_name": agent_name}

    change_row = hist.data[0]
    change_at = change_row["created_at"]

    # Pre-change: 7 days before; post-change: since change
    pre = (
        client.table("admin_agent_stats_daily")
        .select("success_count, error_count, avg_duration_ms, total_calls")
        .eq("agent_name", agent_name)
        .lt("stat_date", change_at[:10])
        .order("stat_date", desc=True)
        .limit(7)
        .execute()
    )
    post = (
        client.table("admin_agent_stats_daily")
        .select("success_count, error_count, avg_duration_ms, total_calls")
        .eq("agent_name", agent_name)
        .gte("stat_date", change_at[:10])
        .execute()
    )

    def _agg(rows):
        if not rows:
            return None
        total = sum(r["total_calls"] for r in rows) or 1
        errors = sum(r["error_count"] for r in rows)
        durations = [r["avg_duration_ms"] for r in rows if r["avg_duration_ms"]]
        return {
            "success_rate": round(1 - errors / total, 3),
            "avg_duration_ms": round(sum(durations) / len(durations), 1) if durations else None,
            "total_calls": total,
        }

    pre_stats = _agg(pre.data or [])
    post_stats = _agg(post.data or [])

    recommend_rollback = False
    reason = "Insufficient data for comparison"
    if pre_stats and post_stats and post_stats["total_calls"] >= 5:
        sr_delta = post_stats["success_rate"] - pre_stats["success_rate"]
        reason = f"Success rate changed {sr_delta:+.1%} since config change on {change_at[:10]}"
        recommend_rollback = sr_delta < -0.05  # >5% success rate drop

    return {
        "agent_name": agent_name,
        "last_config_change": change_at,
        "pre_change_stats": pre_stats,
        "post_change_stats": post_stats,
        "recommend_rollback": recommend_rollback,
        "reason": reason,
        "rollback_history_id": change_row["id"] if recommend_rollback else None,
    }
```

### Frontend: Diff Display Component (shell)

```tsx
// Pattern: AdminAgent admin pages use 'use client' + useCallback + fetch with Authorization header
// Source: integrations/page.tsx, analytics/page.tsx established patterns
'use client';

interface DiffPanelProps {
  diff: string;  // unified diff string from backend
}

export function DiffPanel({ diff }: DiffPanelProps) {
  return (
    <pre className="text-xs font-mono bg-gray-900 rounded p-4 overflow-x-auto whitespace-pre-wrap">
      {diff.split('\n').map((line, i) => (
        <span
          key={i}
          className={
            line.startsWith('+') ? 'text-green-400' :
            line.startsWith('-') ? 'text-red-400' :
            line.startsWith('@@') ? 'text-blue-400' :
            'text-gray-300'
          }
        >
          {line + '\n'}
        </span>
      ))}
    </pre>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Feature flags = env vars only (current `feature_flags.py`) | DB-backed flags with Redis TTL, env vars as fallback | Phase 12 | Enables runtime toggle without redeploy |
| Agent instructions hardcoded in Python source | DB-stored, injected at runner creation | Phase 12 | Enables admin editing without code deploy |
| Autonomy tiers only modifiable via DB migration | Editable via AdminAgent confirm-tier tool and UI | Phase 12 | Live reconfiguration of agent behavior boundaries |

---

## Open Questions

1. **Should DB-stored agent instructions completely replace the hardcoded Python instruction?**
   - What we know: Python source has the canonical instruction; DB has editable version
   - What's unclear: On first deploy, DB table is empty — need a seed or fallback to Python source
   - Recommendation: Seed `admin_agent_configs` with the current hardcoded instruction for each agent in the migration. At runner creation, read from DB and fall back to Python constant if row missing. This preserves the existing behavior as the default.

2. **Agent instruction hot-reload for the current AdminAgent session**
   - What we know: Per-request ADK Runner means each message creates a new Runner; instructions are passed at Runner creation
   - What's unclear: Does the ADK Runner accept `instruction` as a parameter override, or does it use the Agent singleton's fixed instruction?
   - Recommendation: Verify in `app/routers/admin/chat.py` how the runner is created. If it uses the singleton `admin_agent`, the instruction needs to be fetched from DB and passed as an override at runner init time (not at module import). This may require a small refactor of the chat endpoint runner creation.

3. **How many feature flags to seed initially?**
   - What we know: `feature_flags.py` currently has 3 env-var-based flags: `WORKFLOW_KILL_SWITCH`, `WORKFLOW_CANARY_ENABLED`, `WORKFLOW_CANARY_USER_IDS`
   - What's unclear: Whether all env-var flags should migrate to DB, or only new ones
   - Recommendation: Seed the migration with the 3 existing flags as rows (defaulting to current env var values). New feature flags from Phase 12+ go to DB. Existing code in `feature_flags.py` that reads env vars remains as a secondary fallback for backward compat.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed in `.planning/config.json`) |
| Config file | `pyproject.toml` or `pytest.ini` (existing) |
| Quick run command | `uv run pytest tests/unit/admin/test_config_tools.py -x` |
| Full suite command | `uv run pytest tests/unit/admin/ -x` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-01 | `generate_instruction_diff` produces unified diff | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_diff_generation -x` | Wave 0 |
| CONF-01 | `validate_instruction_content` blocks injection patterns | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_injection_validation -x` | Wave 0 |
| CONF-02 | `get_config_history` returns ordered version list | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_get_config_history -x` | Wave 0 |
| CONF-02 | `rollback_agent_config` confirm-tier writes to DB + history | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_rollback_config -x` | Wave 0 |
| CONF-03 | `toggle_feature_flag` confirm-tier sets DB + invalidates Redis | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_toggle_feature_flag -x` | Wave 0 |
| CONF-03 | `get_flag()` reads Redis first, falls back to DB | unit | `uv run pytest tests/unit/admin/test_config_service.py::test_flag_cache_hit -x` | Wave 0 |
| CONF-04 | `update_autonomy_permission` writes new tier to admin_agent_permissions | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_update_autonomy -x` | Wave 0 |
| CONF-05 | Config API CRUD endpoints require admin auth | unit | `uv run pytest tests/unit/admin/test_config_api.py -x` | Wave 0 |
| SKIL-07 | `assess_config_impact` returns workflow list for known agent | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_assess_impact -x` | Wave 0 |
| SKIL-08 | `recommend_config_rollback` recommends rollback on >5% sr drop | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_rollback_recommendation -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/admin/test_config_tools.py -x`
- **Per wave merge:** `uv run pytest tests/unit/admin/ -x`
- **Phase gate:** `uv run pytest tests/unit/admin/ -x` full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/admin/test_config_tools.py` — 10 tool tests (CONF-01 through SKIL-08)
- [ ] `tests/unit/admin/test_config_service.py` — `get_flag()` Redis/DB fallback logic
- [ ] `tests/unit/admin/test_config_api.py` — REST endpoint auth + response shape tests

*(Existing test infrastructure in `tests/unit/admin/conftest.py` with mock_supabase_client and admin_user_dict fixtures covers all new test files — no framework changes needed)*

---

## Database Migration Design

The Phase 12 migration needs to:
1. Create `admin_agent_configs` table
2. Create `admin_feature_flags` table
3. Seed `admin_agent_configs` with all 10 specialized agent names + their current hardcoded instructions (or empty placeholder if instructions are too long for a migration — use minimal seed)
4. Seed `admin_feature_flags` with the 3 existing env-var flags
5. Seed `admin_agent_permissions` with 10 new config-domain tool rows

**Timestamp:** Must be > `20260322500000` (last migration in chain). Use `20260323000000`.

**Agent names to seed** (from `app/agents/admin/agent.py` and `app/agents/specialized_agents.py`):
`financial`, `content`, `strategic`, `sales`, `marketing`, `operations`, `hr`, `compliance`, `customer_support`, `data`

---

## Sources

### Primary (HIGH confidence)

- Python stdlib `difflib` module — verified in Python 3.10 docs, no external dependency
- Project codebase: `supabase/migrations/20260321300000_admin_panel_foundation.sql` — `admin_config_history` schema confirmed (lines 112-124)
- Project codebase: `app/services/feature_flags.py` — confirmed env-var-only implementation, 3 flags
- Project codebase: `app/workflows/registry.py` — WorkflowRegistry with `list_by_category()` method confirmed at line 65
- Project codebase: `app/agents/admin/tools/_autonomy.py` — confirmed `check_autonomy()` pattern
- Project codebase: `app/agents/admin/agent.py` — confirmed FAST_AGENT_CONFIG, per-request runner pattern, existing tool list
- Project codebase: `supabase/migrations/20260320400000_telemetry_schema.sql` — `agent_telemetry` and `admin_agent_stats_daily` schemas confirmed

### Secondary (MEDIUM confidence)

- Redis SETEX with 60s TTL: standard Redis pattern, used extensively in `app/services/cache.py` — circuit breaker pattern is project-established

### Tertiary (LOW confidence)

- Specific injection pattern regex — based on well-known prompt injection taxonomy; not from an authoritative LLM security standard. Validate against current OWASP LLM Top 10 before finalizing.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all key technologies (stdlib diff, Redis, Supabase, existing autonomy pattern) are already in use in the project
- Architecture: HIGH — patterns directly derived from Phase 7, 10, 11 established in codebase
- Pitfalls: HIGH for items 1-4 (derived from project code analysis); MEDIUM for item 5 (injection rollback — general security reasoning)
- SKIL-07/08 tools: HIGH — WorkflowRegistry and admin_agent_stats_daily both confirmed in codebase with exact APIs identified

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable internal stack, no external library updates required)
