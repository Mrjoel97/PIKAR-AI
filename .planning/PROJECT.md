# Project: pikar-ai

## Current State

- Latest shipped milestone: **v1.1 Production Readiness** on 2026-03-13
- Archive status: v1.1 roadmap and requirements are now stored in `.planning/milestones/`
- Delivery summary: 5 phases (2-6), 8 completed plans, 24 of 24 v1.1 requirements complete
- Current planning mode: no active execution phase; the repo is ready for next-milestone definition work

## Next Milestone Goals

1. Define the problem statement, scope boundaries, and success criteria for **v2.0 Strategic Nurturing**.
2. Convert deferred ideas into a fresh milestone-scoped requirements file before new roadmap phases are written.
3. Decide whether to run a retrospective `$gsd-audit-milestone` for v1.1 so the shipped milestone has a formal audit artifact.
4. Clear the local tooling follow-ups surfaced during v1.1 verification, especially a later `supabase link` and a `uv.lock` refresh in a full `uv lock` environment.

## Shipped v1.1 Highlights

- Aligned the active Supabase schema/runtime contract and removed stale Alembic migration surfaces.
- Eliminated blocking async Supabase/cache paths across the affected service layer.
- Repaired frontend/backend auth, type, and SSE integration seams.
- Added production security headers, stricter auth/CORS handling, and upload-size guardrails.
- Unified configuration/deployment behavior with Docker health signaling and shared SSE connection limits.

## Archived Context

<details>
<summary>Pre-closeout project snapshot (captured before v1.1 archival)</summary>

## Vision
To be the ultimate AI "Chief of Staff" and business growth engine, empowering non-technical users to transform vague ideas into thriving autonomous ventures through a highly orchestrated ecosystem of specialized agents.

## Core Goals
1. **Intelligent Orchestration:** Seamlessly delegate complex business tasks from a central Executive Agent to specialized domain experts (Finance, Marketing, Strategy, etc.).
2. **Autonomous Growth:** Provide a structured, agent-led pathway for evolving business concepts into operational entities.
3. **Operational Excellence:** Harden existing workflows and agentic protocols to ensure deterministic and reliable business management.
4. **Interoperable Ecosystem:** Utilize the A2A protocol for cross-framework agent collaboration.

## High-Level Architecture
- **Executive Layer:** Root ADK `LlmAgent` orchestrating sub-agents and tool calls.
- **Service Layer:** FastAPI backend providing SSE streaming, task management, and API routing.
- **Workflow Layer:** YAML-defined dynamic workflows executed via a centralized engine.
- **Persistence Layer:** Supabase (PostgreSQL) for state, session, and task storage, with Redis for performance acceleration.
- **Client Layer:** Next.js (TypeScript) frontend with real-time interactive widgets.

## Current Milestone At The Time

**Milestone:** v1.1 Production Readiness

**Goal:** Bridge all gaps between codebase and Supabase database, fix frontend-backend alignment, resolve async blocking, and harden security for production deployment.

**Target features:**
- Database alignment: create 3 missing tables, add missing column to skills
- Async service fixes: migrate ~40 blocking .execute() calls to execute_async()
- Frontend-backend alignment: CORS headers, auth consistency, type mismatches
- Security hardening: headers, config unification, token encryption
- Alembic cleanup and deployment readiness

## Requirement Snapshot

### Validated

- Workflow execution standardization (v1.0 Milestone 1)
- Redis circuit breakers for cache lookups (v1.0 Milestone 1)
- Deterministic argument mapping for workflow tools (v1.0 Milestone 1)

### Active

- [ ] Database schema alignment with codebase
- [ ] Async event-loop safety across all services
- [ ] Frontend-backend API and type alignment
- [ ] Security headers and production hardening
- [ ] Configuration system unification

### Out of Scope

- Strategic nurturing flow enhancements - deferred to v1.2
- New feature development - this milestone is remediation only
- Mobile app or new UI features - not in scope

## Key Stakeholders
- **Primary Users:** Non-technical entrepreneurs and business owners.
- **Developers:** Senior AI/Backend Engineers focused on agentic reliability and framework extension.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase migrations are source of truth (not Alembic) | Supabase has 96 migrations vs 1 stale Alembic file | Pending at snapshot time |
| Skip research phase for v1.1 | This is remediation of known issues, not new features | Pending at snapshot time |

---
*Snapshot source last updated: 2026-03-12 after deep codebase + Supabase analysis*

</details>
