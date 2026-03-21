# Feature Research

**Domain:** AI-first admin panel for a multi-agent SaaS platform
**Researched:** 2026-03-21
**Confidence:** HIGH (grounded in approved design spec + existing codebase patterns; web search corroborates industry norms)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features an admin panel user (the founder) assumes exist. Missing any of these makes the panel feel unfinished or unsafe.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Secure admin gate (auth check before any `/admin/*` route) | Any admin area without a hard gate is a security hole | LOW | Two-layer: env allowlist + `user_roles` DB table. `require_admin` FastAPI dependency. `AdminGuard` in Next.js layout. Must be server-side only — never `NEXT_PUBLIC_` prefix. |
| User search + filter table | Founders need to find specific users quickly | LOW | Name, email, persona, status, signup date, last active. Pagination required. |
| User suspend / unsuspend | Support escalations and abuse management | LOW | Confirm-tier in agent. Logs to audit trail. No user-facing error must leak reason. |
| Comprehensive audit trail | Regulatory hygiene and accountability | MEDIUM | Source-tagged rows (`manual`, `ai_agent`, `impersonation`). Queryable by agent. Indexed on `(admin_user_id, created_at DESC)`. |
| System health overview | Founder needs to know if the product is up | MEDIUM | Aggregates existing `/health/*` endpoints. Status grid with response-time sparklines. |
| API key storage for external tools | Connecting Sentry, PostHog, etc. without code deploys | MEDIUM | Fernet-encrypted in DB. Frontend shows only `****last4`. Never returned decrypted to client. |
| Basic usage metrics (DAU/MAU, messages, workflows) | Founders track growth every day | MEDIUM | Query from existing Supabase tables. KPI cards with sparklines. |
| Persistent AI chat panel | The whole premise of the admin panel — "ask, don't click" | HIGH | ADK AdminAgent on FastAPI, SSE via fetchEventSource (same pattern as existing `useAgentChat`). Docked bottom panel, expandable. Persists across all `/admin/*` pages. |
| Confirm-before-execute flow for destructive agent actions | Agents taking irreversible actions without approval is a trust-killer | MEDIUM | Inline confirmation card rendered in chat. Confirm sends approval token back to agent. Cancel aborts and logs. |
| Audit log viewer page | Admins need to review what happened and when | LOW | Filterable log table at `/admin/audit-log`. Queryable by agent via `check_audit_log` tool. |

### Differentiators (Competitive Advantage)

Features that make this admin panel genuinely better than a standard CRUD dashboard for a solo founder running an AI-first product.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Tiered autonomy permission system (auto / confirm / blocked) | Fine-grained trust calibration per action category — founder decides what the agent can do alone | MEDIUM | `admin_agent_permissions` table. Configurable per action from `/admin/settings`. Defaults: reads=auto, writes=confirm, destructive=blocked. Checked at tool invocation time, not just at system prompt generation. |
| AI Admin Assistant with 30+ domain tools | One natural-language interface replaces 8+ separate dashboards — orders-of-magnitude efficiency for a solo founder | HIGH | Google ADK AdminAgent (`app/agents/admin/agent.py`). Tool domains: users, monitoring, health, integrations, analytics, config, billing, approvals. |
| Proactive greeting on panel open | Agent surfaces actionable state immediately — "3 approvals waiting, 1 Sentry error spike since yesterday" — reduces cognitive overhead | MEDIUM | Requires health summary, incident query, approval count, and integration status all available at startup. Builds on agent context from previous sessions. |
| Self-healing API monitoring loop | Detects and remediates common failures (Redis disconnect, Gemini rate limits, 5xx spikes) without founder intervention | HIGH | Cloud Scheduler triggers `/admin/monitoring/run-check` every 60s. Incident detection + auto-remediation for `auto`-tier failures. `confirm`-tier remediation proposes plan in chat. |
| Admin impersonation with view and interactive modes | Debug user-reported issues in the exact same UX the user sees, without a separate login | HIGH | `ImpersonationContext` overrides `PersonaContext`. Persistent banner. View mode: all admins. Interactive mode: `super_admin` only. Auto-expires in 30 min. All actions tagged `impersonation` in audit trail. |
| Agent configuration editor with version history and rollback | Change agent instructions and roll back safely — no ad hoc SQL edits | MEDIUM | `admin_config_history` table tracks previous/new value, changed_by, change_source. Rollback invokable from agent or UI. |
| Cross-user approval oversight with admin override | Founder can unblock any user's stuck approval without impersonating them | LOW | Extends existing approval workflow. `override_approval` tool is `confirm`-tier. Reason field required on override. |
| Fernet-encrypted integration API key management | Add/rotate external tool credentials from the UI — no redeploy cycle | MEDIUM | Application-layer encryption. Key in `ADMIN_ENCRYPTION_KEY` env var (or Secret Manager in prod). Rotation script re-encrypts all keys. Transparent to frontend. |
| Per-agent effectiveness analytics | Know which of the 10 agents is underperforming — direct feedback loop for tuning | MEDIUM | Success rate, avg response time, satisfaction proxy per agent. Charts in `/admin/analytics`. Also surfaced by agent via `get_agent_effectiveness` tool. |
| Feature flag toggles from admin UI | Toggle features on/off without code changes or redeployment | LOW | Simple JSONB config table. Agent can flip flags via `toggle_feature` (confirm-tier). |
| Retention cohort analysis | Understand whether users come back — week-over-week cohort view | HIGH | Requires query design against chat/workflow activity tables. Likely the most complex analytics feature. |
| Billing / revenue dashboard with Stripe | MRR, ARR, churn, LTV at a glance — no third-party tool needed for basic metrics | MEDIUM | Stripe read-only key recommended. `get_revenue_metrics` tool. Plan distribution chart. Refund capability is `confirm`-tier. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time WebSocket monitoring feed | "Live" feels more premium | Adds a persistent WebSocket infrastructure layer that the project explicitly doesn't use. Polling every 30s or SSE on-demand is indistinguishable from WebSockets for admin health checks at this scale. | SSE or 30s polling for the monitoring dashboard. Cloud Scheduler runs the health check loop every 60s — UI polling to match that cadence is sufficient. |
| Admin mobile app | Founders are sometimes mobile | Admin actions (suspend users, review incidents, modify agent configs) require careful deliberate interaction — mobile increases accidental action risk. Desktop-first is the right constraint for safety. | Responsive design so the panel is usable on tablet in a pinch, but not a first-class mobile experience. |
| Multi-tenant admin (multiple admin teams) | Useful when the company grows | Premature for founder-only stage. Adds role matrix complexity that obscures what's actually needed now. The `user_roles` schema supports it later with zero migration pain. | Current two-layer system (`super_admin` / `admin`) is sufficient. Expand to teams when there's a second human admin. |
| AI-generated code deployments from admin chat | "Have the agent push a hotfix" | Catastrophic blast radius if the agent makes a mistake. No test/review cycle. Mixing admin operations with code deployment creates two different failure modes in one conversation. | Agent can surface the GitHub PR / CodeRabbit review and link to deployment status. Actual code changes stay in a code review workflow. |
| Storing decrypted API keys in browser localStorage | Convenient for UI pre-fill | Exposed to XSS. API keys in localStorage survive origin leaks. | Backend always stores Fernet-encrypted. Frontend shows only `****last4`. Re-entry required for key rotation (intentional friction). |
| Bulk-delete users from admin chat | "Clean up test accounts" | A single misworded agent prompt deletes real users. The existing `delete_user` tool is `blocked` by default, which is the right call. | Keep `delete_user` blocked-tier. Promote to `confirm`-tier only with explicit admin request. Soft-delete (suspend) is the safe default for user management. |
| Custom admin theming | "Make it look different from the user UI" | Creates a parallel design system to maintain. Not zero cost. The visual separation via admin header, impersonation banner, and sidebar is sufficient to distinguish context. | Uses the existing Tailwind/Lucide/Sonner design system with subtle admin-specific accents (e.g., amber for impersonation banner). |
| Embedding full Sentry / PostHog iframes | "See all their data inline" | Cross-origin iframe restrictions, session management complexity, and fragile embedding behavior. The proxy pattern is more controllable and agent-queryable. | Server-side proxy to their APIs. Surface key data in the admin panel as first-class cards. Deep link to Sentry/PostHog for full detail. |

---

## Feature Dependencies

```
Admin Auth Gate (two-layer: env + DB roles)
    └──required by──> Every other admin feature
                         └──required by──> AI Admin Assistant
                                               └──required by──> All AI tool domains

Audit Log Table
    └──required by──> Impersonation (tags actions as 'impersonation')
    └──required by──> AI Agent Tool Execution (tags as 'ai_agent')
    └──required by──> Config History rollback (tracks change_source)

Fernet Encryption Utilities
    └──required by──> External Integrations (Sentry, PostHog, CodeRabbit, GitHub, Stripe)
    └──required by──> Billing Dashboard (Stripe key storage)

API Health Check Tables (api_health_checks + api_incidents)
    └──required by──> Monitoring Dashboard
    └──required by──> Self-Healing Tools in AI Agent
    └──required by──> Proactive Agent Greeting

admin_agent_permissions Table
    └──required by──> Tiered Autonomy Enforcement in All Agent Tools
    └──enhanced by──> Permissions UI (/admin/settings)
    [Note: Tools work with defaults before Permissions UI is built]

External Integrations (Phase 5)
    └──required by──> Sentry/PostHog/CodeRabbit/GitHub tools in AI Agent
    └──enhances──> Analytics (PostHog events can supplement internal analytics)

User Management (Phase 3)
    └──required by──> Admin Impersonation (needs user search to initiate)
    └──enhances──> Cross-user Approval Oversight (user context on approval)

Config History Table
    └──required by──> Agent Config Editor with Rollback (Phase 6)
    [Note: Table can be created in Phase 1 for zero migration cost later]
```

### Dependency Notes

- **Auth gate required by everything:** No admin feature is safe to deploy without Phase 1's `require_admin` dependency in place.
- **Audit log required by impersonation:** The impersonation security model relies on audit trail tagging. Build them together.
- **Fernet utils required by integrations:** Phase 5 (Integrations) cannot store API keys without the encryption utilities from Phase 1.
- **Config history table is a Phase 1 freebie:** Creating it in Phase 1 migration costs nothing and removes a blocker for Phase 6 rollback.
- **Permissions UI is a Phase 9 enhancement, not a blocker:** Agent tools check `admin_agent_permissions` table and fall back to sensible defaults (reads=auto, writes=confirm, destructive=blocked) if no row exists. The UI is for adjustment, not for initial function.
- **Proactive greeting requires multiple Phase 2+ features:** It can be scaffolded in Phase 1 (just system health) and enriched in later phases as incident, approval, and integration data become available.

---

## MVP Definition

This is a subsequent milestone on an existing product. "MVP" here means the minimum admin panel that replaces ad hoc Supabase queries and manual interventions.

### Launch With (Phase 1-3 core)

- [x] **Admin auth gate** — Without it, nothing is safe to deploy
- [x] **AI Admin Assistant (base)** — Core premise of the panel. At minimum: health check tools, system context in system prompt.
- [x] **Audit trail** — Required for impersonation security and agent accountability
- [x] **API health monitoring loop + dashboard** — Replaces manual `/health/*` endpoint polling; highest operational value after auth
- [x] **User management (search, suspend/unsuspend, persona switch)** — Replaces direct Supabase queries for the most common support action
- [x] **Admin impersonation (view mode)** — Replaces "ask user for a screenshot" support loop
- [x] **Confirm-before-execute flow** — Trust foundation; without this, agent feels unsafe to use

### Add After Validation (Phase 4-6)

- [ ] **Usage analytics dashboards** — Add when there are enough users to make the charts meaningful
- [ ] **External integrations (Sentry, PostHog, CodeRabbit, GitHub)** — Add when the product is in production and errors/events need monitoring
- [ ] **Agent config editor with versioning** — Add when prompt tuning becomes a regular activity
- [ ] **Feature flag toggles** — Add when you have features that need gradual rollout
- [ ] **Interactive impersonation mode** — Add after view mode is validated as safe; requires `super_admin` gate

### Future Consideration (Phase 7-9)

- [ ] **Cross-user approval oversight + admin override** — Add when user volume makes approval backlogs real
- [ ] **Billing / revenue dashboard** — Add when Stripe is connected and revenue is non-trivial
- [ ] **Permissions UI (/admin/settings)** — Add when default autonomy tiers need customization; defaults cover the solo-founder phase
- [ ] **Retention cohort analysis** — Add when there are enough cohorts (3+ months of users) to make the chart meaningful
- [ ] **Bulk CSV export / bulk email to users** — Add when user count makes manual outreach impractical

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Admin auth gate | HIGH | LOW | P1 |
| AI Admin Assistant (base chat + health tools) | HIGH | HIGH | P1 |
| Audit trail (table + viewer) | HIGH | LOW | P1 |
| Confirm-before-execute flow | HIGH | MEDIUM | P1 |
| API health monitoring loop | HIGH | MEDIUM | P1 |
| Health dashboard (/admin/monitoring) | HIGH | LOW | P1 |
| User management (list, suspend, persona) | HIGH | LOW | P1 |
| Admin impersonation (view mode) | HIGH | MEDIUM | P1 |
| Fernet encryption utilities | HIGH | LOW | P1 |
| Usage analytics (DAU/MAU/messages) | MEDIUM | MEDIUM | P2 |
| External integrations (Sentry, PostHog) | MEDIUM | MEDIUM | P2 |
| Agent config editor + version history | MEDIUM | MEDIUM | P2 |
| Feature flag toggles | MEDIUM | LOW | P2 |
| Interactive impersonation mode | MEDIUM | MEDIUM | P2 |
| Cross-user approval oversight | MEDIUM | LOW | P2 |
| Tiered autonomy permissions UI | MEDIUM | LOW | P2 |
| Billing dashboard (Stripe) | MEDIUM | MEDIUM | P2 |
| Per-agent effectiveness analytics | MEDIUM | MEDIUM | P2 |
| External integrations (CodeRabbit, GitHub) | LOW | MEDIUM | P3 |
| Retention cohort analysis | LOW | HIGH | P3 |
| Bulk CSV export / bulk email | LOW | LOW | P3 |
| Proactive greeting (full, multi-domain) | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch (Phase 1-3)
- P2: Should have, add when validated (Phase 4-8)
- P3: Nice to have, future consideration (Phase 9+)

---

## Competitor Feature Analysis

This is an internal-facing admin tool, so "competitors" are the patterns used by comparable SaaS admin panels and AI agent frameworks, not direct product competitors.

| Feature | Standard SaaS Admin (e.g., Retool, custom CRUD) | AI-Augmented Admin (e.g., Microsoft 365 Admin AI) | Our Approach |
|---------|----------------------------------------------|-------------------------------------------------|--------------|
| Primary interface | Tables and forms | Tables + Copilot sidebar | AI chat as primary, tables as drill-down |
| Action execution | Direct button click | Copilot suggests, admin executes | Agent proposes, confirm card in chat, admin approves |
| Permission model | Role-based access control | RBAC + AI governance policies | Two-layer auth + per-action autonomy tiers in DB |
| External tool data | iframes or separate tabs | Linked dashboards | Server-side proxy with agent-queryable API |
| Impersonation | View-only via session override | Not standard | View + interactive modes, impersonation banner, audit tagging |
| Health monitoring | Uptime ping + external services (PagerDuty) | Azure Monitor integration | Embedded Cloud Scheduler loop + incident table + AI remediation |
| Audit trail | Action log table | M365 compliance center | Source-tagged log (`manual` / `ai_agent` / `impersonation`) |
| Agent config management | Not applicable | Model deployment settings | Per-agent instruction editor with versioned history + rollback |

---

## Dependencies on Existing System

The following existing infrastructure is directly reused (zero rebuild needed):

| Existing Asset | How Admin Panel Uses It |
|----------------|------------------------|
| `fetchEventSource` + `useAgentChat` hook pattern | Admin chat uses identical `useAdminChat` hook — same SSE pattern |
| Google ADK agent factory pattern (`app/agents/*/agent.py`) | AdminAgent follows same structure as existing 10 specialized agents |
| Gemini Pro → Flash fallback | AdminAgent inherits same model config and retry strategy |
| Supabase service role client | All admin tables accessed via service role (same as `approvals.py`) |
| Redis circuit breaker | Monitoring tools can query circuit breaker state via existing `app/services/cache.py` |
| `slowapi` rate limiting | Admin endpoints use same rate limiter, new route-specific limits |
| Cloud Scheduler + `WORKFLOW_SERVICE_SECRET` pattern | Health check loop reuses same `scheduled_endpoints.py` authentication pattern |
| Existing `/health/*` endpoints | `check_system_health` tool aggregates these — no new health logic needed |
| Existing approval workflow (`/approval/[token]`) | Cross-user approval oversight is a read layer on existing approval records |
| Supabase migrations chain | All 9 new admin tables added via new migration files, no schema modification |
| Fernet (`cryptography` package) | Already a transitive dependency — no new package needed |

---

## Sources

- Design spec: `docs/superpowers/specs/2026-03-21-admin-panel-design.md` (HIGH confidence — approved, detailed)
- [AI Agent Autonomy Levels — Knight First Amendment Institute](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1)
- [Human-in-the-loop confirmation — AWS Bedrock Agents](https://aws.amazon.com/blogs/machine-learning/implement-human-in-the-loop-confirmation-with-amazon-bedrock-agents/)
- [Human-in-the-loop patterns — Cloudflare Agents](https://developers.cloudflare.com/agents/guides/human-in-the-loop/)
- [Secure HITL interactions — Auth0](https://auth0.com/blog/secure-human-in-the-loop-interactions-for-ai-agents/)
- [User impersonation risks — Authress](https://authress.io/knowledge-base/academy/topics/user-impersonation-risks)
- [Audit logging best practices — StrongDM](https://www.strongdm.com/blog/audit-logging)
- [API Health Monitoring beyond health checks — dotcom-monitor](https://www.dotcom-monitor.com/blog/api-health-monitoring/)
- [API Health Check patterns — api7.ai](https://api7.ai/blog/tips-for-health-check-best-practices)
- [SaaS Feature Flags guide — designrevision](https://designrevision.com/blog/saas-feature-flags-guide)
- [Feature flags best practices — LaunchDarkly](https://launchdarkly.com/blog/what-are-feature-flags/)
- [Stripe SaaS analytics — Stripe](https://stripe.com/resources/more/saas-analytics)
- [PostHog vs Sentry comparison](https://posthog.com/blog/posthog-vs-sentry)
- [New AI admin capabilities — Microsoft Ignite 2025](https://techcommunity.microsoft.com/blog/microsoft365copilotblog/new-capabilities-for-ai-admins-from-ignite-2025/4478906)

---

*Feature research for: AI-first admin panel (pikar-ai v3.0)*
*Researched: 2026-03-21*
