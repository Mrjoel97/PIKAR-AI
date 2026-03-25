# Phase 14: Billing Dashboard - Research

**Researched:** 2026-03-25
**Domain:** Stripe billing metrics, AdminAgent tools (billing domain), analytics intelligence skills
**Confidence:** HIGH

## Summary

Phase 14 builds on top of fully-complete Phase 11 infrastructure (IntegrationProxyService, Fernet-encrypted Stripe key in `admin_integrations`, `_fetch_stripe_summary` helper, 300s TTL) and the existing `subscriptions` table (created in migration `20260324400000_subscriptions.sql`). The core work is: (1) new Stripe fetch functions for MRR/ARR/churn/refund metrics, (2) 6 new AdminAgent billing tools in `app/agents/admin/tools/billing.py`, (3) a billing API router at `app/routers/admin/billing.py`, and (4) the `/admin/billing` frontend page with KPI cards and a plan distribution chart.

The `subscriptions` table is the primary data source for plan distribution, churn approximation, and revenue forecasting — it is populated by Stripe webhooks and always reflects the latest subscription state. Live Stripe API calls (through IntegrationProxyService) provide accurate MRR/ARR from the current period amounts. Refunds use `stripe.Refund.create()` with the existing asyncio.to_thread SDK pattern and are confirm-tier actions logged to the audit trail.

The four AI skills (SKIL-05 anomaly detection, SKIL-06 executive summary, SKIL-10 forecasting, SKIL-11 refund risk) are implemented as AdminAgent system-prompt reasoning sections plus helper tools that provide the raw data — same pattern as SKIL-01/SKIL-02 (Phase 11) and SKIL-03/SKIL-04 (Phase 13).

**Primary recommendation:** Build the three-plan sequence: (1) billing Stripe fetch functions + API router + DB migration for permission seeds, (2) AdminAgent billing tools with skills, (3) frontend billing dashboard page.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLT-03 | Admin can view billing dashboard (MRR, ARR, churn, plan distribution) | `subscriptions` table provides plan distribution and churn approximation; Stripe API via IntegrationProxyService provides live MRR/ARR; new `/admin/billing/summary` endpoint aggregates both sources |
| SKIL-05 | AdminAgent detects statistical anomalies in DAU/MAU and agent effectiveness (>2 std dev from 30-day baseline) | `get_usage_stats` + `get_agent_effectiveness` already return 30-day historical data; new `detect_analytics_anomalies` tool computes stddev Python-side from that data |
| SKIL-06 | AdminAgent generates executive summary narratives from raw analytics with actionable recommendations | New `generate_executive_summary` tool calls existing analytics + billing tools, builds narrative text from structured output — same pattern as `generate_report` in Phase 10 |
| SKIL-10 | AdminAgent forecasts MRR/ARR trends from historical subscription data | New `forecast_revenue` tool queries `subscriptions` table for 30-day historical data and computes linear extrapolation; degrades gracefully to "insufficient data" when <7 data points |
| SKIL-11 | AdminAgent assesses refund risk by cross-referencing customer LTV, usage, and subscription tenure | New `assess_refund_risk` tool queries `subscriptions` + `admin_analytics_daily` for the customer's user_id; returns LTV estimate, usage level, tenure, and risk recommendation before `issue_refund` is called |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stripe | >=7.0.0 | Stripe Python SDK | Already used in `integration_proxy.py`; typed responses, auto-pagination, idempotency |
| asyncio.to_thread | stdlib | Wrap synchronous Stripe SDK calls | Established pattern from Phase 11 — all sync SDK calls wrapped in to_thread |
| IntegrationProxyService | internal | Cache-check → fetch → cache-set proxy | Already built Phase 11; Stripe TTL=300s already set |
| supabase-py (service client) | project dep | Query `subscriptions` table | Same client used by all admin tools |
| recharts 3.x | npm | Plan distribution pie/bar chart | Already used in Phase 10 analytics (accessibilityLayer=false, isAnimationActive=false) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| statistics (stdlib) | stdlib | stddev computation for SKIL-05 | Python-side stddev from 30-day DAU/MAU arrays — no external dep needed |
| Lucide icons (DollarSign, TrendingUp, Users, AlertTriangle) | npm | Billing KPI icons | Consistent with all existing admin dashboard icon usage |

### Installation
No new dependencies — `stripe>=7.0.0` is already in `pyproject.toml` (added in Phase 11).

---

## Architecture Patterns

### Recommended Project Structure
```
app/
├── agents/admin/tools/
│   └── billing.py           # 6 new billing tools (SKIL-05, SKIL-06, SKIL-10, SKIL-11)
├── routers/admin/
│   └── billing.py           # GET /admin/billing/summary endpoint
├── routers/admin/__init__.py # Add billing router
└── services/
    └── integration_proxy.py  # Add _fetch_stripe_metrics(), _fetch_stripe_refunds(),
                              # _create_stripe_refund() helpers

frontend/src/
├── app/(admin)/billing/
│   └── page.tsx             # Billing dashboard page
└── components/admin/billing/
    ├── BillingKpiCards.tsx  # MRR, ARR, churn rate, active subs KPI cards
    └── PlanDistributionChart.tsx  # Pie/bar chart of tier breakdown
```

### Pattern 1: Stripe Fetch Functions (integration_proxy.py extension)
**What:** Add private `_fetch_stripe_metrics` and `_create_stripe_refund` helpers that follow the exact same signature as existing `_fetch_stripe_summary`: `async def _fetch_*(api_key, config, params) -> ...`
**When to use:** Any new Stripe data source needs a fetch function injected into IntegrationProxyService.call()

```python
# Source: existing pattern in app/services/integration_proxy.py
def _get_stripe_metrics_sync(api_key: str, params: dict) -> dict:
    import stripe
    # Use auto_paging_iter for full dataset
    subscriptions = stripe.Subscription.list(
        api_key=api_key, limit=100, status="active",
        expand=["data.items.data.price"]
    )
    subs = list(subscriptions.auto_paging_iter())
    # MRR: sum of monthly-equivalent amounts
    mrr = sum(
        (item.price.unit_amount or 0) / 100
        / (12 if item.price.recurring.interval == "year" else 1)
        for sub in subs
        for item in sub["items"]["data"]
    )
    return {"mrr": round(mrr, 2), "arr": round(mrr * 12, 2), "active_count": len(subs)}

async def _fetch_stripe_metrics(api_key, config, params):
    return await asyncio.to_thread(_get_stripe_metrics_sync, api_key, params)
```

### Pattern 2: Billing Tool Structure (billing.py)
**What:** Follow the exact pattern from `integrations.py` — autonomy check, `_get_integration_config("stripe")`, budget check, then `IntegrationProxyService.call()` or direct DB query.
**When to use:** All 6 new billing tools

```python
# Source: established pattern from app/agents/admin/tools/integrations.py
from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.agents.admin.tools.integrations import _get_integration_config
from app.services.integration_proxy import IntegrationProxyService, check_session_budget

async def get_billing_metrics() -> dict:
    gate = await _check_autonomy("get_billing_metrics")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("stripe")
    if isinstance(cfg, dict):
        return cfg   # error dict (not configured / inactive)
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(session_id=_DEFAULT_SESSION_ID, provider="stripe")
    if not allowed:
        return {"error": "Session budget exhausted for stripe. Try again later."}

    return await IntegrationProxyService.call(
        provider="stripe",
        operation="get_metrics",
        api_key=api_key,
        config=config,
        params={},
        fetch_fn=_fetch_stripe_metrics,
    )
```

### Pattern 3: Refund Tool (confirm-tier)
**What:** `issue_refund` is a confirm-tier action. It calls `_check_autonomy("issue_refund")` which returns a confirmation request dict (with `requires_confirmation=True`) on the first call. The actual `stripe.Refund.create()` runs only after the admin confirms with a `confirmation_token`.
**When to use:** Any Stripe write operation

```python
# Source: established confirm-tier pattern from Phase 7
async def issue_refund(
    charge_id: str,
    amount_cents: int | None = None,
    reason: str = "requested_by_customer",
    confirmation_token: str | None = None,
) -> dict:
    gate = await _check_autonomy("issue_refund")
    if gate is not None:
        return gate  # Returns {requires_confirmation: True, ...}

    # confirmation_token validated by confirmation service (Phase 7)
    # Only reaches here after admin confirms
    cfg = await _get_integration_config("stripe")
    if isinstance(cfg, dict):
        return cfg
    api_key, _config, _base_url = cfg

    result = await asyncio.to_thread(
        _create_refund_sync, api_key, charge_id, amount_cents, reason
    )
    await log_admin_action(action="issue_refund", ...)
    return result
```

### Pattern 4: Subscriptions Table for Plan Distribution
**What:** Query the `subscriptions` table (service client, bypasses RLS) for plan distribution and churn approximation. This is faster than Stripe API and doesn't consume the session budget.
**When to use:** Plan distribution, churn rate calculation, revenue forecasting

```python
# Source: established pattern from app/agents/admin/tools/analytics.py
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

client = get_service_client()
query = (
    client.table("subscriptions")
    .select("tier, is_active, will_renew, current_period_end, created_at")
    .order("created_at", desc=True)
)
result = await execute_async(query, op_name="billing.plan_distribution")
rows = result.data or []
```

**Churn rate calculation from `subscriptions` table:**
- Churned = `is_active=false` OR `will_renew=false` — these represent cancelled/lapsed subscriptions
- Churn rate (monthly) = churned_this_month / (active_start_of_month + new_this_month)
- Use `current_period_end` and `last_event_type` fields for monthly window

### Pattern 5: SKIL-05 Anomaly Detection (Python stddev)
**What:** Call existing `get_usage_stats(days=30)` and `get_agent_effectiveness(days=30)` tools internally, then compute mean + stddev using `statistics.stdev()` on the daily arrays. Flag values >2 stddev from the mean.
**When to use:** SKIL-05 anomaly detection tool

```python
import statistics

async def detect_analytics_anomalies(days: int = 30) -> dict:
    gate = await _check_autonomy("detect_analytics_anomalies")
    if gate is not None:
        return gate

    usage = await get_usage_stats(days=days)
    agent_data = await get_agent_effectiveness(days=days)

    dau_values = [row["dau"] for row in usage.get("usage_trends", []) if row.get("dau")]
    anomalies = []

    if len(dau_values) >= 3:
        mean_dau = statistics.mean(dau_values)
        stdev_dau = statistics.stdev(dau_values)
        latest_dau = dau_values[0]
        if stdev_dau > 0 and abs(latest_dau - mean_dau) > 2 * stdev_dau:
            anomalies.append({
                "metric": "dau",
                "current": latest_dau,
                "mean": round(mean_dau, 1),
                "stddev": round(stdev_dau, 1),
                "deviation": round((latest_dau - mean_dau) / stdev_dau, 2),
            })
    # Repeat for MAU, agent success rates
    return {"anomalies": anomalies, "period_days": days}
```

### Pattern 6: API Router (billing.py)
**What:** Follow the existing `analytics.py` router pattern — single GET endpoint with `require_admin` dependency, `@limiter.limit("120/minute")`, queries both `subscriptions` table and Stripe integration proxy.
**When to use:** `/admin/billing/summary` endpoint

```python
# Source: established pattern from app/routers/admin/analytics.py
@router.get("/billing/summary")
@limiter.limit("120/minute")
async def get_billing_summary(
    request: Request,
    admin_user: dict = Depends(require_admin),
) -> dict[str, Any]:
    # 1. Query subscriptions table for plan distribution + churn
    # 2. Call Stripe via IntegrationProxyService for live MRR/ARR (if configured)
    # Graceful degradation: if Stripe not configured, return subscriptions-table data only
    ...
```

### Pattern 7: Frontend Page (page.tsx)
**What:** Same structure as `analytics/page.tsx` — `'use client'`, `useCallback` fetch, `useEffect` with polling, loading skeleton, error state, Tailwind dark-mode classes. Billing-specific: 4 KPI cards + plan distribution chart.

```typescript
// Source: established pattern from analytics/page.tsx
const REFRESH_INTERVAL_MS = 60_000;  // 60s — pre-cached data, same as analytics
```

### Anti-Patterns to Avoid
- **Using STRIPE_API_KEY env var directly in admin tools:** The admin billing tools MUST use the Fernet-encrypted key from `admin_integrations` table, NOT the `STRIPE_API_KEY` env var. The `StripeMCPTool` in `app/mcp/tools/stripe_payments.py` uses the env var — that is user-facing and separate. Admin tools use `_get_integration_config("stripe")`.
- **Calling Stripe API for plan distribution:** Use the `subscriptions` table (local DB) for plan distribution and churn. Reserve Stripe API calls for MRR/ARR where live data is essential. Protects against session budget exhaustion.
- **Refund without audit log:** All writes to Stripe (refunds) must call `log_admin_action()` after success, same as user management mutations in Phase 9.
- **Exposing Stripe charge IDs or customer IDs to the frontend:** The billing API returns aggregated metrics only. Refunds are executed via AdminAgent tool (confirm-tier), not via a frontend REST endpoint.
- **asyncio.gather with Stripe calls:** The asyncio.to_thread pattern wraps synchronous SDK calls one at a time. Do NOT use asyncio.gather with multiple to_thread Stripe calls — Phase 19 learned that serialization is safer for SDK-based calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MRR computation | Custom subscription math | `stripe.Subscription.list(expand=["data.items.data.price"])` via SDK | Stripe provides recurring amounts with interval normalization; building from scratch misses trials, discounts, prorations |
| Plan distribution | Custom Stripe customer iteration | `subscriptions` table | Table is webhook-synced, always current, no API call budget consumed |
| Confirmation flow for refunds | New token system | Phase 7 `_check_autonomy("issue_refund")` returning `requires_confirmation=True` | Already built; reuse exact same flow as suspend_user, toggle_feature_flag |
| Anomaly detection | External ML library | `statistics.stdev()` Python stdlib | Simple 2-stddev threshold over 30 daily points; no ML needed at this scale |
| Caching Stripe responses | Custom TTL store | `IntegrationProxyService.call(ttl=300)` | Already built; 5-min Stripe TTL prevents rate exhaustion in admin chat sessions |
| Revenue forecasting | External forecasting library | Linear extrapolation from 30-day MRR history in `subscriptions` table | At 30 days of data, simple linear regression is accurate and transparent; complex models overfit |

---

## Common Pitfalls

### Pitfall 1: Stripe Key Confusion (Critical)
**What goes wrong:** Developer uses `os.environ.get("STRIPE_API_KEY")` in admin billing tools, exposing the env-var key instead of the admin-configured Fernet-encrypted key. The env var is the user-facing key for `StripeMCPTool`; the admin tools should use the key stored in `admin_integrations`.
**Why it happens:** `StripeMCPTool` in `app/mcp/tools/stripe_payments.py` uses the env var pattern and is tempting to copy.
**How to avoid:** Always call `_get_integration_config("stripe")` from `app/agents/admin/tools/integrations.py` in all admin billing tools. The env-var key path should never appear in `app/agents/admin/tools/billing.py`.
**Warning signs:** Any import of `os` or `os.environ` in billing.py.

### Pitfall 2: Blocking Event Loop with Stripe SDK
**What goes wrong:** `stripe.Subscription.list()`, `stripe.Refund.create()`, and all Stripe SDK calls are synchronous. Calling them directly in an async function blocks the event loop.
**Why it happens:** The SDK looks like a normal Python library and doesn't obviously require thread wrapping.
**How to avoid:** All Stripe SDK calls must be wrapped in `asyncio.to_thread()` — the same pattern established in Phase 11 for `_get_stripe_summary_sync`.
**Warning signs:** `stripe.Subscription.list(...)` called without `await asyncio.to_thread(...)`.

### Pitfall 3: MRR Formula Errors
**What goes wrong:** Treating all `items.data[0].price.unit_amount` as monthly without normalizing annual subscriptions. A $1200/year plan shows as $1200 MRR instead of $100.
**Why it happens:** Easy to miss `price.recurring.interval` normalization.
**How to avoid:** Check `price.recurring.interval` — divide by 12 for `year`, use as-is for `month`. Return raw amounts in cents and divide by 100 for display.

### Pitfall 4: Churn Rate Formula — Will_Renew vs Is_Active
**What goes wrong:** Using `is_active=false` alone to measure churn misses users who are still in their last paid period but have cancelled (will_renew=false). This under-reports churn.
**Why it happens:** The `is_active` field looks like the obvious churn signal.
**How to avoid:** Count `will_renew=false AND is_active=true` as "pending churn" and include them in the churn rate numerator. Use `billing_issue_at IS NOT NULL` to identify past_due separately.

### Pitfall 5: Stripe Budget Exhaustion in Skills
**What goes wrong:** SKIL-06 (executive summary) and SKIL-11 (refund risk) each call multiple tools internally; if each calls Stripe, a single admin question consumes multiple budget slots.
**Why it happens:** Skills call other tools — tool chaining multiplies budget consumption.
**How to avoid:** Skills that need billing data should call `get_billing_metrics()` once and pass the result to sub-computations. Do not call `get_billing_metrics()` in both `generate_executive_summary` and `assess_refund_risk` independently.

### Pitfall 6: Migration Timestamp Collision
**What goes wrong:** Using `20260324XXXXXX` timestamps when the last migration is `20260324400000_subscriptions.sql`.
**Why it happens:** Easy to pick an arbitrary timestamp in the same-day range.
**How to avoid:** Phase 14 permission-seed migration must use timestamp `20260325000000` or later. The subscriptions migration already occupies `20260324400000`.

---

## Code Examples

### MRR Calculation (Stripe SDK)
```python
# Source: Stripe Python SDK pattern (stripe>=7.0.0), verified from Phase 11 SDK usage
def _get_stripe_metrics_sync(api_key: str) -> dict:
    import stripe
    subs = list(stripe.Subscription.list(
        api_key=api_key,
        limit=100,
        status="active",
        expand=["data.items.data.price"],
    ).auto_paging_iter())

    mrr_cents = 0
    for sub in subs:
        for item in sub["items"]["data"]:
            price = item.get("price", {})
            amount = price.get("unit_amount") or 0
            interval = (price.get("recurring") or {}).get("interval", "month")
            if interval == "year":
                amount = amount // 12
            mrr_cents += amount

    return {
        "mrr": round(mrr_cents / 100, 2),
        "arr": round(mrr_cents / 100 * 12, 2),
        "active_subscriptions": len(subs),
    }
```

### Refund Creation (Stripe SDK, asyncio.to_thread)
```python
# Source: established asyncio.to_thread pattern from Phase 11 integration_proxy.py
def _create_refund_sync(api_key: str, charge_id: str, amount_cents: int | None, reason: str) -> dict:
    import stripe
    params = {"charge": charge_id, "reason": reason}
    if amount_cents is not None:
        params["amount"] = amount_cents
    refund = stripe.Refund.create(api_key=api_key, **params)
    return {
        "refund_id": refund.id,
        "status": refund.status,
        "amount": refund.amount,
        "currency": refund.currency,
        "charge": refund.charge,
    }

async def _execute_refund(api_key, charge_id, amount_cents, reason):
    return await asyncio.to_thread(_create_refund_sync, api_key, charge_id, amount_cents, reason)
```

### Plan Distribution from subscriptions Table
```python
# Source: established pattern from app/agents/admin/tools/analytics.py
client = get_service_client()
query = client.table("subscriptions").select("tier, is_active, will_renew")
result = await execute_async(query, op_name="billing.plan_distribution")
rows = result.data or []

from collections import Counter
tier_counts = Counter(r["tier"] for r in rows if r.get("is_active"))
plan_distribution = [
    {"tier": tier, "count": count}
    for tier, count in tier_counts.most_common()
]
```

### Permission Seed SQL (billing tools)
```sql
-- Source: established pattern from 20260321600000_user_management_permissions.sql
INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('billing', 'get_billing_metrics',         'auto',    'low',    'Fetch live MRR/ARR from Stripe'),
    ('billing', 'get_plan_distribution',        'auto',    'low',    'Get subscription tier breakdown from DB'),
    ('billing', 'detect_analytics_anomalies',   'auto',    'low',    'Detect stddev anomalies in DAU/MAU'),
    ('billing', 'generate_executive_summary',   'auto',    'low',    'Generate analytics narrative with recommendations'),
    ('billing', 'forecast_revenue',             'auto',    'low',    'Project MRR/ARR from historical trend'),
    ('billing', 'assess_refund_risk',           'auto',    'low',    'Cross-reference LTV and usage before refund'),
    ('billing', 'issue_refund',                 'confirm', 'high',   'Issue Stripe refund — requires confirmation')
ON CONFLICT (action_category, action_name) DO NOTHING;
```

### Frontend KPI Card Pattern
```typescript
// Source: established pattern from frontend/src/components/admin/analytics/KpiCards.tsx
interface BillingKpiCardsProps {
  mrr: number;
  arr: number;
  churnRate: number;
  activeSubscriptions: number;
  dataSource: 'live' | 'db_only' | 'no_data';
}

// Format MRR/ARR as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
```

### Frontend Chart (recharts 3.x)
```typescript
// Source: Phase 10 recharts 3.x established patterns (accessibilityLayer=false, isAnimationActive=false)
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

// PLAN_COLORS maps tier names to brand colors
const PLAN_COLORS: Record<string, string> = {
  free: '#6b7280',
  solopreneur: '#3b82f6',
  startup: '#8b5cf6',
  sme: '#f59e0b',
  enterprise: '#10b981',
};

<ResponsiveContainer width="100%" height={200}>
  <PieChart>
    <Pie
      data={planDistribution}
      dataKey="count"
      nameKey="tier"
      accessibilityLayer={false}    // Phase 10 pattern: removes ARIA noise on polling dashboards
      isAnimationActive={false}     // Phase 10 pattern: no animation overhead
    >
      {planDistribution.map((entry) => (
        <Cell key={entry.tier} fill={PLAN_COLORS[entry.tier] ?? '#6b7280'} />
      ))}
    </Pie>
    <Tooltip />
  </PieChart>
</ResponsiveContainer>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct Stripe API calls in tools | IntegrationProxyService.call() with 300s cache | Phase 11 | No re-hitting Stripe on repeated admin questions in same session |
| ENV-var Stripe key in admin tools | Fernet-encrypted key in `admin_integrations` table | Phase 11 | Key rotation without redeploy; audit trail of when key was changed |
| MRR from charges list | MRR from active subscriptions list with price expand | Current Stripe best practice | Subscriptions are the source of truth for recurring revenue; charges include one-offs |
| Churn from is_active only | Churn from is_active + will_renew + billing_issue_at | Schema design in Phase 14 | Captures pending cancellations and payment failures as distinct churn signals |
| Anomaly detection with external libraries (numpy/scipy) | Python stdlib statistics.stdev() | Kept simple for this use case | No additional dependencies; 30 data points is within stdlib capabilities |

---

## Tool Count: ASST-02 Progress

The current AdminAgent has 49 exported tools (counted from `__init__.py` `__all__` list). Phase 14 adds 7 new tools:

| Tool | Tier | Requirement |
|------|------|-------------|
| get_billing_metrics | auto | ANLT-03 |
| get_plan_distribution | auto | ANLT-03 |
| issue_refund | confirm | ANLT-03 (success criterion 2) |
| detect_analytics_anomalies | auto | SKIL-05 |
| generate_executive_summary | auto | SKIL-06 |
| forecast_revenue | auto | SKIL-10 |
| assess_refund_risk | auto | SKIL-11 |

After Phase 14: **56 tools** — well past the 30+ ASST-02 target. ASST-02 will be complete after Phase 14.

---

## Open Questions

1. **Stripe charge_id for refund: how does admin get it?**
   - What we know: `stripe.Refund.create()` requires a `charge` ID (chs_xxx). The `subscriptions` table stores `stripe_subscription_id` but not individual charge IDs.
   - What's unclear: Is there a preceding `get_recent_charges(customer_id)` tool needed, or does the admin provide the charge ID from context?
   - Recommendation: Add a `get_customer_charges(user_id)` auto-tier tool that looks up the customer's recent charges from Stripe (using `stripe_customer_id` from `subscriptions` table). The admin would call this first, then `assess_refund_risk`, then `issue_refund`. This makes the flow: identify → assess risk → confirm refund.

2. **MRR historical data: no time-series in subscriptions table**
   - What we know: The `subscriptions` table has a `created_at` and `updated_at` but no per-day MRR snapshot. SKIL-10 forecasting needs historical MRR data points.
   - What's unclear: Whether to compute "current MRR at each webhook event date" from the Stripe API's subscription history, or use a simpler heuristic.
   - Recommendation: For Phase 14, compute approximate historical MRR from `subscriptions` rows grouped by `tier` and their `created_at` dates (new subs per month × average price per tier). This gives a reasonable 3-month trend without needing Stripe's API history endpoint. Document this as an approximation.

3. **Stripe restricted key: read-only vs read-write for refunds**
   - What we know: Phase description says "restricted read-only Stripe key that limits blast radius." But refunds require write access to the Stripe API.
   - What's unclear: Should the admin configure two keys (read-only for metrics, write for refunds), or one key with restricted write access?
   - Recommendation: One key with restricted permissions scoped to: `subscriptions:read`, `charges:read`, `balance:read`, `refunds:write`. Document in the admin UI that the Stripe key needs refund write access. The Fernet encryption and confirm-tier gate together limit blast radius; true read-only key is not practical when refunds are a stated requirement.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/unit/admin/test_billing_tools.py -x` |
| Full suite command | `uv run pytest tests/unit/admin/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLT-03 | `get_billing_metrics` returns MRR/ARR from IntegrationProxyService | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_get_billing_metrics_returns_data -x` | ❌ Wave 0 |
| ANLT-03 | `get_plan_distribution` returns tier counts from subscriptions table | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_get_plan_distribution_returns_tiers -x` | ❌ Wave 0 |
| ANLT-03 | `issue_refund` returns confirmation request on first call (confirm tier) | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_issue_refund_requires_confirmation -x` | ❌ Wave 0 |
| ANLT-03 | `issue_refund` calls Stripe and logs audit action after confirmation | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_issue_refund_executes_after_confirmation -x` | ❌ Wave 0 |
| ANLT-03 | GET /admin/billing/summary returns 200 with MRR, ARR, plan_distribution fields | unit | `uv run pytest tests/unit/admin/test_billing_api.py::test_billing_summary_returns_200 -x` | ❌ Wave 0 |
| ANLT-03 | GET /admin/billing/summary degrades gracefully when Stripe not configured | unit | `uv run pytest tests/unit/admin/test_billing_api.py::test_billing_summary_no_stripe -x` | ❌ Wave 0 |
| SKIL-05 | `detect_analytics_anomalies` flags DAU >2 stddev from 30-day mean | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_detect_anomalies_flags_dau -x` | ❌ Wave 0 |
| SKIL-05 | `detect_analytics_anomalies` returns empty anomalies when data is stable | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_detect_anomalies_no_flag_stable -x` | ❌ Wave 0 |
| SKIL-06 | `generate_executive_summary` returns summary_text with actionable recommendation | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_generate_executive_summary_returns_text -x` | ❌ Wave 0 |
| SKIL-10 | `forecast_revenue` returns next_month_mrr projection from historical data | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_forecast_revenue_projects_trend -x` | ❌ Wave 0 |
| SKIL-10 | `forecast_revenue` returns insufficient_data flag when <7 data points | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_forecast_revenue_insufficient_data -x` | ❌ Wave 0 |
| SKIL-11 | `assess_refund_risk` returns risk_level HIGH when LTV low + short tenure | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_assess_refund_risk_high -x` | ❌ Wave 0 |
| SKIL-11 | `assess_refund_risk` returns risk_level LOW when LTV high + long tenure | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_assess_refund_risk_low -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/admin/test_billing_tools.py -x`
- **Per wave merge:** `uv run pytest tests/unit/admin/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_billing_tools.py` — covers all 7 billing tools (ANLT-03, SKIL-05 through SKIL-11)
- [ ] `tests/unit/admin/test_billing_api.py` — covers GET /admin/billing/summary endpoint

*(Existing test infrastructure in `tests/unit/admin/conftest.py` covers shared fixtures — no new conftest needed.)*

---

## Sources

### Primary (HIGH confidence)
- `app/services/integration_proxy.py` — IntegrationProxyService.call() signature, `_fetch_stripe_summary` pattern, 300s TTL, asyncio.to_thread pattern for Stripe SDK
- `app/agents/admin/tools/integrations.py` — `_get_integration_config()` helper, budget check pattern, tool structure with autonomy gate
- `app/agents/admin/tools/analytics.py` — `get_usage_stats`, `get_agent_effectiveness` tool implementations (SKIL-05/06 will call these)
- `app/agents/admin/tools/__init__.py` — complete tool registry (49 tools pre-Phase 14)
- `app/agents/admin/agent.py` — AdminAgent instruction pattern for new billing skill sections
- `supabase/migrations/20260324400000_subscriptions.sql` — subscriptions table schema (tier, is_active, will_renew, billing_issue_at, stripe_customer_id)
- `supabase/migrations/20260321600000_user_management_permissions.sql` — permission seed SQL pattern
- `app/routers/admin/analytics.py` — GET endpoint pattern (require_admin, limiter, execute_async)
- `frontend/src/app/(admin)/analytics/page.tsx` — frontend page pattern (useCallback, polling, skeleton, error state)
- `frontend/src/components/admin/analytics/KpiCards.tsx` — KPI card component pattern

### Secondary (MEDIUM confidence)
- Stripe Python SDK documentation (as of Phase 11 implementation in this codebase): `stripe.Subscription.list(expand=["data.items.data.price"])` for MRR computation, `stripe.Refund.create()` for refunds
- Python stdlib `statistics.stdev()` for SKIL-05 anomaly detection (no external dependency)
- recharts 3.x `accessibilityLayer=false` + `isAnimationActive=false` patterns established in Phase 10

### Tertiary (LOW confidence)
- Stripe restricted key permission scoping recommendation — LOW confidence, needs validation against Stripe Dashboard's actual permission model for the "Restricted keys" feature

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use in this codebase; no new dependencies
- Architecture: HIGH — patterns directly copied from Phase 11 (integrations) and Phase 10 (analytics); no new patterns invented
- Pitfalls: HIGH — Stripe key confusion and event loop blocking verified from Phase 11 decisions in STATE.md
- Skills implementation: MEDIUM — stddev anomaly detection and linear regression are simple; the LTV approximation in SKIL-11 involves estimation logic that will need the planner to define precise business rules

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (Stripe SDK stable; recharts 3.x established in codebase)
