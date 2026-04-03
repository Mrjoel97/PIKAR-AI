# Project: pikar-ai

## What This Is

A multi-agent AI executive system ("Chief of Staff") built on Google ADK that orchestrates 10 specialized agents through a central ExecutiveAgent. It empowers non-technical users to transform business ideas into operational ventures via intelligent agent-led workflows — including an AI-powered app builder that takes users from a vague idea to a deployable web/mobile app through a guided creative workflow. Frontend is Next.js 16 with React 19, backend is FastAPI/Supabase.

## Core Value

Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations — now including building the digital assets (landing pages, web apps, mobile apps) they need through a GSD-style creative workflow.

## Current Milestone: v6.0 Real-World Integration & Solopreneur Unlock

**Goal:** Transform Pikar from an AI advice system into a real-world action platform. Add genuine external integrations (CRM, accounting, ads, e-commerce, project management), fix the solopreneur persona to be full-featured single-user (not limited), rename misleading tools for trust, and fill every capability gap identified in the comprehensive value audit.

**Key philosophy change:** Solopreneur is NOT a limited tier. It is a single-user category with full access to workflows, approvals, sales, reports, compliance, financial forecasting, and all real-value features. The ONLY difference from other personas is team/collaboration features. A solopreneur should run a one-person business without limitations.

**Target features:**
- Solopreneur persona unlocked: full access to workflows, dynamic workflow generator, approvals, sales pipeline, reports, compliance, financial forecasting
- Misleading tool rename: `manage_hubspot` → guide, `run_security_audit` → checklist, `deploy_container` → guide, etc.
- CRM integration: HubSpot API connector (read/write contacts, deals, pipelines)
- Accounting/financial sync: Stripe revenue auto-import into financial_records
- Project management integration: Linear/Asana API connector (sync tasks/issues)
- Email automation: Gmail-based sequences, auto-categorization, CRM-linked tracking
- Ad platform integration: Google Ads + Meta Ads API (create/manage/optimize campaigns)
- E-commerce integration: Shopify API connector (orders, products, analytics)
- Document generation: PDF reports, pitch decks, proposals from agent output
- Data import/export: CSV import, bulk operations, data migration tools
- Webhook/Zapier connector: General-purpose webhook system + Zapier integration
- Slack/Teams notifications: Push notifications to team chat platforms
- Team collaboration: Shared workspaces, collaborative editing, permission roles
- External data analytics: Connect to user's Postgres/BigQuery/Sheets for real analysis
- Calendar automation: Smart scheduling, auto-follow-ups, recurring task automation
- Continuous intelligence: Scheduled competitor/market/industry monitoring pipeline

## Requirements

### Validated

- ✓ Workflow execution standardization — v1.0
- ✓ Redis circuit breakers for cache lookups — v1.0
- ✓ Deterministic argument mapping for workflow tools — v1.0
- ✓ Database schema alignment with codebase — v1.1
- ✓ Async event-loop safety across all services — v1.1
- ✓ Frontend-backend API and type alignment — v1.1
- ✓ Security headers and production hardening — v1.1
- ✓ Configuration system unification — v1.1
- ✓ Stitch MCP singleton integration with DB schema and asset persistence — v2.0
- ✓ GSD creative workflow engine (7-stage guided flow) — v2.0
- ✓ Creative questioning and design research — v2.0
- ✓ Design brief with user-approved design system — v2.0
- ✓ Screen variant generation and side-by-side preview — v2.0
- ✓ Iteration loop with version history and rollback — v2.0
- ✓ Multi-page builder with baton-loop pattern — v2.0
- ✓ React/TypeScript conversion pipeline — v2.0
- ✓ Output targets (PWA, Capacitor, Remotion video) — v2.0
- ✓ Ship pipeline with SSE progress streaming — v2.0

### Active

**v4.0 Production Scale & Persona UX (97% complete):**
- ✓ Multi-worker app server, distributed SSE, persona dashboards, feature flags, security hardening — v4.0
- ✓ Persona navigation, default widgets, empty states, onboarding checklists — v4.0

**v5.0 Persona Production Readiness:**
- [ ] Soft feature gating per persona tier (hide/show + upgrade prompts, no payment enforcement)
- [ ] Backend persona awareness in ExecutiveAgent
- [ ] Shell header KPIs wired to real computed data
- [ ] Multi-user foundations (invite, teams, shared workspaces)
- [ ] RBAC system (roles, permissions, role assignment)
- [ ] Audit trail system (governance logs)
- [ ] Real department coordination for SME
- [ ] Enterprise portfolio health and risk coverage metrics
- [ ] Persona-specific agent instructions

**v3.0 Admin Panel (Phases 14-15, remaining):**
- [ ] Billing dashboard, approval oversight, permissions, role management

**Deferred from v2.0 (Phase 23, not yet planned):**
- [ ] Builder dashboard with project status and resume capability
- [ ] One-click deploy to public URL

### Out of Scope

- Multi-tenant admin (multiple admin teams) — founder-only for now, expandable later
- Real-time WebSocket monitoring — SSE/polling sufficient for admin use
- Custom admin theming — uses existing app design system
- Admin mobile app — desktop-first admin panel
- Native iOS/Android development (Swift/Kotlin) — Capacitor hybrid covers mobile
- Backend/server-side code generation — UI/frontend generation only
- E-commerce checkout flows — beyond UI generation scope

## Context

- 10 specialized ADK agents (financial, content, strategic, sales, marketing, operations, HR, compliance, support, data)
- Frontend: Next.js 16, React 19, Tailwind CSS 4, Supabase auth, fetchEventSource SSE chat
- Backend: FastAPI, Google ADK, Gemini models with Pro→Flash fallback, Redis with circuit breaker
- App Builder: Stitch MCP singleton (Node.js subprocess), 15+ API routes, SSE streaming for build/ship, ~14,900 LOC Python + ~1,800 LOC TypeScript
- Existing chat uses `useAgentChat` hook with `@microsoft/fetch-event-source` — admin chat follows same pattern
- Existing health endpoints: /health/live, /health/connections, /health/cache, /health/embeddings, /health/video
- Persona-based routing (solopreneur/startup/sme/enterprise) but no true RBAC exists
- slowapi rate limiting already in use across routers
- Full design spec: `docs/superpowers/specs/2026-03-21-admin-panel-design.md`

## Constraints

- **Existing Infra**: Must use existing patterns (ADK agents, fetchEventSource SSE, Supabase migrations, Cloud Scheduler)
- **Python AI**: Admin agent must be a Google ADK agent on FastAPI (not a separate Node.js AI SDK setup)
- **Schema Extension**: Add new admin tables via Supabase migrations, do not modify existing tables
- **Security**: API keys encrypted with Fernet, admin emails never exposed in client bundle
- **Backward Compat**: Admin panel must not affect existing user-facing routes or functionality

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase migrations are source of truth (not Alembic) | Supabase has 96 migrations vs 1 stale Alembic file | ✓ Good |
| AI-first admin (chat-centered, not dashboard-centered) | Solo founder efficiency — one interface for all admin domains | ✓ Good |
| Google ADK AdminAgent (not Vercel AI SDK) | Consistent with existing chat infra, direct backend service access | ✓ Good |
| Two-layer auth (env allowlist + DB roles) | Bootstrap via env, transition to DB, OR logic for flexibility | ✓ Good |
| Fernet encryption for integration API keys | Application-layer encryption, key in env/Secret Manager, supports rotation | ✓ Good |
| Cloud Scheduler for health monitoring loop | Consistent with existing scheduled_endpoints.py pattern | ✓ Good |
| Server-side admin email check (not NEXT_PUBLIC_) | Prevents leaking admin identities in client bundle | ✓ Good |
| is_admin() SECURITY DEFINER function | Avoids circular self-referencing RLS on user_roles table | ✓ Good |
| Individual message rows (not JSONB blob) | Avoids write amplification, enables partial loading/querying | ✓ Good |
| Stitch MCP over REST API | MCP provides richer tools (edit_screens, project management) and follows stitch-skills standard | ✓ Good |
| GSD-style creative workflow | Guided discovery → brief → build → verify, not just "prompt → generate" — differentiates from v0/Bolt/Lovable | ✓ Good |
| User screen preview before creation | Creative control — preview variants, iterate, then finalize | ✓ Good |
| Capacitor for hybrid mobile | Native-like mobile from React output without requiring native dev skills | ✓ Good |
| Design system persistence per project | Visual consistency across multi-page apps, follows stitch-skills DESIGN.md pattern | ✓ Good |
| Prompt enhancer for screen generation | Gemini transforms vague user input into Stitch-optimized prompts with domain vocabulary | ✓ Good |
| Self-contained npm version resolution per generator | Avoids cross-service imports in parallel wave execution | ✓ Good |

| Solopreneur = full-featured single-user | Solopreneur locked out of workflows was wrong — they need automation most | — Pending |
| Real integrations over knowledge wrappers | Tools named after actions must perform those actions, or be renamed | — Pending |

---
*Last updated: 2026-04-03 after v6.0 Real-World Integration & Solopreneur Unlock milestone started*
