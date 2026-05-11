# Phase 109: Workflow Node Editor — Phase 1 (Read-only Viewer) — Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Source:** `docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md` (Spec B)

<domain>
## Phase Boundary

**This phase delivers ONLY Phase 1 of Spec B** — a read-only graph viewer for existing workflow templates. No editing, no save, no branching, no execution changes.

What ships:
1. A SQL migration that adds `graph_nodes`, `graph_edges`, `graph_layout` JSONB columns to `workflow_templates`, plus three Postgres helper functions that project existing linear `steps` lists into graph form. The migration eagerly populates these columns for every existing row (per locked decision #4: eager, not lazy).
2. The FastAPI `/workflows/templates` and `/workflows/templates/{id}` endpoints return the new graph fields in their response payloads.
3. A new Next.js route `/dashboard/workflows/editor/[id]` that renders any template as a static React Flow graph (read-only, no editing). The existing template-card "Edit" / "View" button routes here.

What does NOT ship in this phase (deferred to Phase 2-4):
- Editing nodes / dragging / connecting edges
- Save mutation, version rows, If-Match concurrency
- Branching, parallel, merge, human-approval node kinds (only `agent-action`, `trigger`, `output` render)
- Engine changes — the graph_nodes columns are purely metadata; execution still walks the legacy `steps` list
- Dual-tab condition expression UX (Phase 3)
- Test-run button (Phase 4)

</domain>

<decisions>
## Implementation Decisions

All six were locked on 2026-05-11 — see Spec B § "Decisions (locked 2026-05-11)" for full prose. The four relevant to Phase 1:

### Decision 3 — Per-user scope
- `workflow_templates.owner_user_id` is the scope key (already exists). Seeded templates have `owner_user_id = NULL` and are treated as read-only global seeds.
- Phase 1 viewer does NOT need new auth — the existing `/workflows/templates` endpoint already filters by owner.

### Decision 4 — Eager migration
- A one-shot `UPDATE workflow_templates SET graph_nodes = pikar.project_steps_to_nodes(steps), ...` runs as part of the deploy migration.
- Errors on individual rows write to a new `workflow_template_migration_errors` table; do not block the migration.
- After Phase 1 deploys, every row has `graph_nodes IS NOT NULL`. The frontend skips the runtime-projection codepath.

### Decision 5 — Version rows (Phase 2)
- Phase 1 does NOT create the `workflow_template_versions` table yet. That's Phase 2.
- Phase 1 writes graph fields directly onto `workflow_templates`, the legacy column-on-row pattern. Phase 2's migration will migrate this into the new versions table.
- This is a small short-term ugliness (Phase 1 graph fields on the row will be redundant once Phase 2 ships) but lets Phase 1 stay focused.

### Decision 6 — If-Match (Phase 2)
- Phase 1 is read-only, so no concurrency surface yet. If-Match plumbing comes in Phase 2.

### Tech choice — React Flow (`@xyflow/react` v12)
- Locked. ~150kb gz. Industry standard. Adds `@xyflow/react` to `frontend/package.json`.
- Auto-layout via the built-in `dagre`-based positioning helper (no separate dependency needed if React Flow's bundled layout works; otherwise add `@dagrejs/dagre`).

### Claude's Discretion
- Naming of the three SQL helper functions (suggested: `pikar.project_steps_to_nodes`, `pikar.project_steps_to_edges`, `pikar.compute_dagre_layout`).
- File layout under `frontend/src/components/workflows/editor/` for read-only components.
- Whether to use a JSONB schema (assumed yes — Decision 5 spec). Server-side validation of the projection helpers' output via Postgres functions, not at the application layer.

</decisions>

<specifics>
## Specific Ideas

- Linear-to-graph projection for a 4-step template `[s1, s2, s3, s4]` produces 6 nodes (`trigger` → s1 → s2 → s3 → s4 → `output`) and 5 edges. See Spec B § "Migration path for existing templates".
- React Flow node kinds for Phase 1 are limited to `trigger`, `agent-action`, `output`. Other kinds (`condition`, `parallel`, `merge`, `human-approval`) are reserved for Phase 3+ but the type union must include them so Phase 1's TypeScript types are forward-compatible.
- The existing `/dashboard/workflows/templates` "Edit" button currently routes to `/dashboard/workflows/editor/new`, which 404s today. Phase 1 makes that "Edit" button on a template card route to `/dashboard/workflows/editor/[template-id]` instead, where the user sees the graph (read-only). The "new" route stays unhandled in Phase 1 (Phase 2 implements editing).

</specifics>

<deferred>
## Deferred Ideas

- All Phase 2-4 work: editing, save, versioning, If-Match, branching, parallel, human-approval, test runs.
- Mobile-friendly viewer (Spec B § "Non-goals").
- Auto-layout fine-tuning (use React Flow's default layout for v1; revisit if user feedback shows layout is bad).
- Multi-language support — Phase 1 is English-only.

</deferred>

---

*Phase: 109-workflow-node-editor-viewer*
*Context gathered: 2026-05-11 from Spec B (decisions locked same day)*
