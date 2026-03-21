# Phase 17: Creative Questioning Engine - Research

**Researched:** 2026-03-21
**Domain:** State-machine workflow UI, FastAPI REST, Next.js App Router, Supabase
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FLOW-01 | User starts an app project and enters GSD-style creative questioning ("What do you want to build?", audience, purpose, style vibe) via structured choice cards — not free text | Answered by: state machine design, creative_brief JSONB schema, FastAPI router pattern, Next.js page structure |
| BLDR-04 | Visual GSD progress bar showing current position in the 7-stage workflow with stage banners | Answered by: stage CHECK constraint on app_projects, build_sessions.stage, framer-motion available, Tailwind progress bar pattern |
</phase_requirements>

---

## Summary

Phase 17 adds the first user-facing layer of the v2.0 App Builder: a structured creative-discovery interview and a 7-stage GSD progress bar. All database infrastructure (app_projects, build_sessions tables with stage enums) landed in Phase 16. Phase 17's job is to wire a FastAPI router that creates app_project + build_session rows, define the discovery question script, and render the questioning UI plus the progress bar in Next.js.

The questioning flow must feel like a creative director interview — short focused questions with choice cards, NOT an open text box. Each answer is stored as a key in app_projects.creative_brief (JSONB). When all questions in the "questioning" stage are answered, the API advances build_sessions.stage (and app_projects.stage) from 'questioning' to 'research', and the frontend progress bar reflects the change immediately via optimistic state update.

There is no ADK/LLM involvement in Phase 17. This is pure state-machine CRUD: create rows, update stage, reflect in UI. Stitch MCP is not called. Prompt enhancer is not called. Those come in Phase 18+.

**Primary recommendation:** Build a thin FastAPI `/app-builder` router (Pydantic models + service-role Supabase writes) and a standalone Next.js page `/app-builder/new` with a multi-step choice-card wizard and a sticky progress bar component. Keep all state local to the page (useState step index + accumulated answers) until the final "start project" submit.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI + Pydantic v2 | (project-pinned) | REST endpoints for project creation and stage transition | Matches every other router in `app/routers/` |
| Supabase Python client | (project-pinned) | Write app_projects + build_sessions rows | get_service_client() pattern already in all routers |
| Next.js App Router | 16.1.4 | `/app-builder` page tree | Project-standard |
| React 19 | 19.2.3 | Multi-step wizard state | useState + useReducer for step/answers |
| Tailwind CSS 4 | (project-pinned) | Progress bar, card grid, stage banners | All existing UI uses Tailwind only |
| Lucide React | 0.563.0 | Stage icons in progress bar | Used throughout — Check, Clock, Zap icons |
| framer-motion | 12.29.0 | Card entrance animations, step transitions | Already installed; used in other components |
| @supabase/ssr | 0.8.0 | Auth session in Next.js Server Components | `@/lib/supabase/client` pattern already established |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@/services/api.ts` (fetchWithAuth) | internal | Authenticated fetch to FastAPI | Use for POST /app-builder/projects and PATCH stage transition |
| `@/contexts/PersonaContext` | internal | userId for API calls | usePersona() already provides userId to all dashboard components |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local React state for wizard | Zustand or URL query params | Local state is sufficient — wizard is single-page, no back-nav needed across sessions |
| Optimistic stage update | Refetch after PATCH | Optimistic update makes progress bar feel instant; revert on error. Same pattern as LandingPagesWidget.tsx |
| framer-motion for step transitions | CSS transitions | framer-motion already installed; AnimatePresence makes step exit/enter cleaner |

**Installation:** No new packages required. All dependencies are present.

---

## Architecture Patterns

### Recommended Project Structure

```
app/routers/
└── app_builder.py          # New: POST /app-builder/projects, PATCH /app-builder/projects/{id}/stage

frontend/src/
├── app/app-builder/
│   ├── layout.tsx           # Shared layout with GSD progress bar (sticky top)
│   ├── new/
│   │   └── page.tsx         # Multi-step questioning wizard
│   └── [projectId]/
│       └── page.tsx         # Project workspace (shell for Phases 18-23)
├── components/app-builder/
│   ├── GsdProgressBar.tsx   # 7-stage progress bar + stage banners
│   ├── QuestionStep.tsx     # Single question with choice cards
│   └── QuestioningWizard.tsx  # Orchestrates steps, accumulates answers
└── services/
    └── app-builder.ts       # createProject(), advanceStage(), getProject()
```

### Pattern 1: Multi-Step Wizard with Local Accumulation

**What:** Each question is a "step" (0–N). User selects a choice card; answer stored in local `answers` state object. On final step, one POST request creates the project row.

**When to use:** The user has not committed to anything yet — no DB row exists until all questions are answered. This avoids creating orphaned draft rows for every user who opens the modal.

**Example:**
```typescript
// QuestioningWizard.tsx
const QUESTIONS: Question[] = [
  { id: 'what',    prompt: 'What do you want to build?',        choices: ['Landing page', 'Web app', 'Mobile app', 'Portfolio', 'E-commerce'] },
  { id: 'who',     prompt: 'Who is this for?',                  choices: ['My business', 'A client', 'My personal brand', 'Just experimenting'] },
  { id: 'purpose', prompt: 'What should visitors do?',          choices: ['Book a call', 'Sign up', 'Buy something', 'Learn about me', 'Browse content'] },
  { id: 'vibe',    prompt: 'Pick a style vibe',                 choices: ['Clean & minimal', 'Bold & energetic', 'Warm & friendly', 'Professional & serious', 'Creative & playful'] },
  { id: 'name',    prompt: 'Give your project a working title', choices: [] },  // free text exception — only one
];

const [step, setStep] = useState(0);
const [answers, setAnswers] = useState<Record<string, string>>({});

const handleSelect = (questionId: string, value: string) => {
  const updated = { ...answers, [questionId]: value };
  setAnswers(updated);
  if (step < QUESTIONS.length - 1) {
    setStep(s => s + 1);  // auto-advance on card selection
  }
};

const handleSubmit = async () => {
  const project = await createProject({ title: answers.name, creative_brief: answers });
  router.push(`/app-builder/${project.id}`);
};
```

### Pattern 2: GSD Progress Bar — Stage-Driven

**What:** A horizontal bar with 7 labeled segments. Current stage highlighted with indigo accent and "YOU ARE HERE" banner. Completed stages show a check icon. Future stages are muted.

**When to use:** Always visible in the app-builder layout, driven by `project.stage` from server.

**Example:**
```typescript
// GsdProgressBar.tsx
const GSD_STAGES = [
  { id: 'questioning', label: 'Questioning', icon: HelpCircle },
  { id: 'research',    label: 'Research',    icon: Search },
  { id: 'brief',       label: 'Brief',       icon: FileText },
  { id: 'building',   label: 'Building',    icon: Hammer },
  { id: 'verifying',  label: 'Verifying',   icon: CheckCircle },
  { id: 'shipping',   label: 'Shipping',    icon: Rocket },
  { id: 'done',       label: 'Done',        icon: Star },
] as const;

const currentIndex = GSD_STAGES.findIndex(s => s.id === currentStage);

// Each segment: completed = green check, current = indigo pulse, future = slate muted
```

### Pattern 3: FastAPI Router — Thin CRUD

**What:** Two endpoints. POST creates `app_projects` + `build_sessions` row atomically (both on same service-role client call). PATCH advances stage on both tables.

**When to use:** All state transitions go through this router — frontend never writes Supabase directly for app_builder domain.

**Example:**
```python
# app/routers/app_builder.py

class ProjectCreateRequest(BaseModel):
    title: str
    creative_brief: dict = {}

class StageAdvanceRequest(BaseModel):
    stage: Literal['questioning', 'research', 'brief', 'building', 'verifying', 'shipping', 'done']

@router.post("/app-builder/projects", status_code=201)
async def create_project(body: ProjectCreateRequest, user_id: str = Depends(get_current_user_id)):
    supabase = get_service_client()
    project_id = str(uuid.uuid4())
    project_data = {
        "id": project_id,
        "user_id": user_id,
        "title": body.title,
        "status": "draft",
        "stage": "questioning",
        "creative_brief": body.creative_brief,
    }
    result = supabase.table("app_projects").insert(project_data).execute()
    # Create linked build_session
    supabase.table("build_sessions").insert({
        "project_id": project_id,
        "user_id": user_id,
        "stage": "questioning",
        "state": {"answers": body.creative_brief},
        "messages": [],
    }).execute()
    return result.data[0]

@router.patch("/app-builder/projects/{project_id}/stage")
async def advance_stage(project_id: str, body: StageAdvanceRequest, user_id: str = Depends(get_current_user_id)):
    supabase = get_service_client()
    result = supabase.table("app_projects").update({"stage": body.stage}).eq("id", project_id).eq("user_id", user_id).execute()
    supabase.table("build_sessions").update({"stage": body.stage}).eq("project_id", project_id).eq("user_id", user_id).execute()
    return result.data[0]
```

### Pattern 4: Creative Brief JSONB Shape

The `app_projects.creative_brief` JSONB will store the answers object from the wizard. The canonical shape for Phase 17:

```json
{
  "what": "Landing page",
  "who": "My business",
  "purpose": "Book a call",
  "vibe": "Clean & minimal",
  "name": "Acme Consulting"
}
```

Phase 18 (design research) will read this and add fields like `competitors`, `palette_suggestion` etc. The schema is append-only; never delete keys.

### Anti-Patterns to Avoid

- **Free-text box for all questions:** Users stall. Choice cards remove the blank-page problem. Only the project name (working title) uses free text — and even this can have suggestions.
- **Creating a DB row per question answered:** Creates orphaned rows. Create the row only on final submit.
- **Calling the prompt enhancer or Stitch in Phase 17:** Not needed — those are Phase 18+. Any call to `generate_app_screen` in this phase is out of scope.
- **Progress bar inside a modal:** The progress bar must be in the layout so it survives page navigations through Phase 18-23. Embed it in `app/app-builder/layout.tsx`, not inside the wizard component.
- **Duplicating stage enum in TypeScript:** Derive from a `const` array (the same `GSD_STAGES` definition), not from separate string literals that can drift from the DB CHECK constraint.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth token injection | Custom auth middleware | `get_current_user_id` from `app/routers/onboarding.py` | Already handles JWT validation via Supabase; 4-line Depends() |
| Supabase client creation | Per-request client | `get_service_client()` from `app/services/supabase` | Handles pooling; same pattern in all 25+ routers |
| Route protection in Next.js | Custom middleware | Existing auth pattern — `createClient()` from `@/lib/supabase/client` in server component | Auth is already wired via middleware.ts |
| Step animation | Custom CSS | `framer-motion` AnimatePresence + motion.div | Already installed; handles exit animations correctly in React 19 |
| Progress calculation | Custom math | Array index of GSD_STAGES[currentStage] | 7 known stages — simple findIndex, no percentage math needed |

**Key insight:** This phase is almost entirely UI + thin REST. The heavy lifting (Stitch calls, prompt enhancement) was done in Phase 16. Don't reach for agent tools — this is CRUD.

---

## Common Pitfalls

### Pitfall 1: RLS Blocks Service-Role Writes
**What goes wrong:** FastAPI uses service-role key for writes; however, `screen_variants.user_id` FKs `auth.users(id)`. If a fake UUID is passed, the FK fails.
**Why it happens:** `app_projects.user_id` has no FK (intentional, from Phase 16 decision), but `screen_variants` does. Phase 17 doesn't touch `screen_variants`, so this is not a risk here — but don't accidentally INSERT into screen_variants from the project creation endpoint.
**How to avoid:** The create_project endpoint only touches `app_projects` and `build_sessions` (both no-FK on user_id). Stay in those two tables.
**Warning signs:** `ForeignKeyViolationError` from Supabase on insert.

### Pitfall 2: Stage Enum Drift Between DB and TypeScript
**What goes wrong:** DB CHECK constraint has 7 values; frontend uses a different list (e.g., missing 'done' or using 'complete').
**Why it happens:** Two separate definitions maintained independently.
**How to avoid:** Define `GSD_STAGES` as a `const` array of objects in a shared TypeScript file (`/types/app-builder.ts`). Derive all stage checks from that single source. On the Python side, use `Literal['questioning', 'research', 'brief', 'building', 'verifying', 'shipping', 'done']` in the Pydantic model — tests catch any mismatch.
**Warning signs:** A stage transition PATCH returns 400 from FastAPI's Literal validator when the frontend sends an unknown value.

### Pitfall 3: Progress Bar Not Updating After Stage Transition
**What goes wrong:** User completes questioning, PATCH succeeds, but progress bar still shows "Questioning" as current.
**Why it happens:** Progress bar reads from React state that isn't updated after the API call — or is derived from a server-fetched project that isn't reloaded.
**How to avoid:** Use optimistic state: after successful PATCH, call `setCurrentStage(newStage)` before the router.push(). The layout component receives stage as prop from the page — pass a callback up, or use a shared context for current project.
**Warning signs:** Stale stage in progress bar despite network tab showing 200 OK on the PATCH.

### Pitfall 4: Choice Cards Blocking on Last Step
**What goes wrong:** User selects the last choice card and nothing happens because `auto-advance` logic fires before the final submit.
**Why it happens:** The auto-advance `setStep(s => s + 1)` increments past the last step index.
**How to avoid:** Guard: `if (step < QUESTIONS.length - 1) setStep(s => s + 1); else setReadyToSubmit(true)`. Show a "Start Building" CTA button on the final step, not auto-advance.
**Warning signs:** UI hangs after last card selection with no submit button visible.

### Pitfall 5: Missing `app_builder` Router Registration in fast_api_app.py
**What goes wrong:** The new router is created but never included in the FastAPI app, so all `/app-builder/*` requests return 404.
**Why it happens:** Developers forget to add both the import and the `app.include_router()` call in `fast_api_app.py`.
**How to avoid:** The plan must explicitly include a task step to add `from app.routers.app_builder import router as app_builder_router` and `app.include_router(app_builder_router, tags=["App Builder"])` to `fast_api_app.py`.
**Warning signs:** Pytest passes, but manual curl returns 404.

---

## Code Examples

Verified patterns from existing codebase:

### Auth Dependency (from onboarding.py)
```python
# Source: app/routers/onboarding.py
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
security = HTTPBearer()

async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    token = credentials.credentials
    supabase = get_supabase_client()
    # Supabase JWT verification happens here
```

### Supabase Service Client Write (from pages.py)
```python
# Source: app/routers/pages.py
from app.services.supabase import get_service_client
supabase = get_service_client()
result = supabase.table("app_projects").insert({...}).execute()
```

### Frontend Authenticated Fetch (from services/landing-pages.ts)
```typescript
// Source: frontend/src/services/landing-pages.ts
async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${session.access_token}` };
}

const res = await fetch(`${API_BASE}/app-builder/projects`, {
  method: 'POST',
  headers: { ...await getAuthHeaders(), 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});
```

### Optimistic State Update (from LandingPagesWidget.tsx)
```typescript
// Source: frontend/src/components/widgets/LandingPagesWidget.tsx
// Optimistic update before API call; revert on error
setCurrentStage('research');  // immediate
try {
  await advanceStage(projectId, 'research');
} catch {
  setCurrentStage('questioning');  // revert
}
```

### framer-motion Step Transition
```typescript
// framer-motion 12.x — AnimatePresence with exit animations
// Source: framer-motion docs pattern, verified installed at 12.29.0
import { AnimatePresence, motion } from 'framer-motion';

<AnimatePresence mode="wait">
  <motion.div
    key={step}
    initial={{ opacity: 0, x: 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
    transition={{ duration: 0.2 }}
  >
    <QuestionStep question={QUESTIONS[step]} onSelect={handleSelect} />
  </motion.div>
</AnimatePresence>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-text "describe your app" onboarding | Choice-card wizard (Typeform-style) | Industry shift ~2023 (Vercel v0, Framer AI) | Higher completion rates; structured data for downstream AI |
| Full-page reload on stage transition | Optimistic update + router.push | React 18+ / Next.js App Router | Instant perceived response |
| Separate DB call for user verification + row write | service-role client (RLS bypassed, auth verified at middleware layer) | Established project pattern | Single round-trip, consistent with all existing routers |

**Deprecated/outdated:**
- Pages Router pattern (`getServerSideProps`): This project uses App Router exclusively. Do not use `getServerSideProps`.

---

## Open Questions

1. **Where in the persona navigation does the App Builder live?**
   - What we know: Personas (`solopreneur`, `startup`, `sme`, `enterprise`) each have a single page at `/(personas)/{persona}/page.tsx` and use `PersonaDashboardLayout`.
   - What's unclear: Should the app builder be `/app-builder/new` (standalone, not inside a persona layout) or nested inside `/solopreneur/app-builder`?
   - Recommendation: Make it standalone at `/app-builder` (sibling to `/(personas)`) — the app builder is a product-level feature, not persona-specific. Add an "App Builder" nav entry to `PremiumShell` in Phase 23 (BLDR-01). For Phase 17, the page is directly accessible by URL; nav integration is deferred.

2. **Should the project title (name) be a free-text input or the last choice-card?**
   - What we know: The spec says "not an open text box" but a working title is inherently free text.
   - What's unclear: Does the spec mean no free text at any point, or "don't start with a blank text box"?
   - Recommendation: Use choice cards for 4 structured questions (what/who/purpose/vibe), then a single text input for the project name as the final step. This follows the Typeform pattern — end with the easy, low-stakes field.

3. **Does the build session need to persist conversation messages in Phase 17?**
   - What we know: `build_sessions.messages` is a JSONB `[]`. Phase 17 doesn't involve an AI chat — it's a click-through wizard.
   - What's unclear: Should Phase 17 write question/answer pairs as fake "messages" for future context, or leave messages empty?
   - Recommendation: Store wizard answers in `build_sessions.state` (JSONB) as `{"answers": {...}}`. Leave `messages` as `[]`. Phase 18 will write real AI messages. Keeps the state schema clean.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest 4.0.18 (frontend) |
| Config file | `pytest.ini` (backend), `frontend/scripts/run-vitest.mjs` |
| Quick run command | `uv run pytest tests/unit/app_builder/ -x` |
| Full suite command | `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLOW-01 | POST /app-builder/projects creates app_project + build_session rows with correct stage='questioning' | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py -x` | Wave 0 |
| FLOW-01 | creative_brief JSONB stores all wizard answers | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_create_project_stores_creative_brief -x` | Wave 0 |
| FLOW-01 | PATCH /app-builder/projects/{id}/stage updates both tables | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_advance_stage -x` | Wave 0 |
| BLDR-04 | GsdProgressBar renders correct stage as active (frontend) | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/GsdProgressBar.test.tsx` | Wave 0 |
| BLDR-04 | Stage transition updates progress bar state | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/QuestioningWizard.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/app_builder/ -x`
- **Per wave merge:** `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/app_builder/test_app_builder_router.py` — covers FLOW-01 (router unit tests with mocked Supabase client)
- [ ] `frontend/src/__tests__/components/GsdProgressBar.test.tsx` — covers BLDR-04 (stage rendering, active highlight)
- [ ] `frontend/src/__tests__/components/QuestioningWizard.test.tsx` — covers FLOW-01 wizard step logic

---

## Sources

### Primary (HIGH confidence)

- Phase 16 SUMMARY files (16-01, 16-02, 16-03) — exact schema, service patterns, project decisions (read directly)
- `supabase/migrations/20260321400000_app_builder_schema.sql` — definitive column names, CHECK constraints, JSONB defaults
- `app/agents/tools/app_builder.py` — ADK tool interface, available tools (generate_app_screen, list_stitch_tools, enhance_description)
- `app/routers/pages.py` + `app/routers/onboarding.py` — router + auth dependency patterns to replicate
- `app/fast_api_app.py` — router registration list (confirmed no app_builder router yet)
- `frontend/src/services/landing-pages.ts` — authenticated fetch + optimistic update pattern
- `frontend/src/components/widgets/LandingPagesWidget.tsx` — UI component pattern (Tailwind, Lucide, state management)
- `frontend/package.json` — confirmed framer-motion 12.29.0, Next.js 16.1.4, React 19.2.3, vitest 4.0.18

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS-v2.md` + `.planning/ROADMAP-v2.md` — phase scope and requirements (project-authored docs)
- `.planning/STATE.md` — locked decisions from prior phases

### Tertiary (LOW confidence)

- Typeform-style wizard UX pattern (industry knowledge, not verified via external source for this project context)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified from package.json and existing router files
- Architecture patterns: HIGH — derived directly from existing router files and Phase 16 decisions
- Pitfalls: HIGH — derived from Phase 16 decisions log and existing codebase conventions
- Test map: HIGH — existing pytest + vitest setup verified from config files

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable stack; DB schema locked by Phase 16 migration)
