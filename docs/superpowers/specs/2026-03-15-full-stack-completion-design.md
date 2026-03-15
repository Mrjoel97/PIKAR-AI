# Plan C: Full-Stack Completion — Design Spec

**Date:** 2026-03-15
**Goal:** Bring Pikar-AI from ~88% to 100% frontend completeness, wire 3 client-only pages to real backend persistence, and polish remaining standard-quality pages to premium level.

**Out of scope:** Stripe Connect (Phase 7) and Pikar-AI Subscriptions (Phase 8) are deferred until the app is ready for real users.

---

## Conventions (All New Routers)

All new FastAPI routers MUST follow the canonical pattern from `app/routers/workflows.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id  # NOT verify_token
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

router = APIRouter(prefix="/support", tags=["Support"])

@router.get("/tickets")
@limiter.limit(get_user_persona_limit)
async def list_tickets(request: Request, user_id: str = Depends(get_current_user_id)):
    ...
```

Key rules:
- Auth: Use `get_current_user_id` (returns `str` user ID from bearer token), NOT `verify_token`
- Rate limiting: Every endpoint uses `@limiter.limit(get_user_persona_limit)` with `request: Request` as first param
- Service initialization: Use `AdminService` with manual `user_id` filtering (consistent with how `SupportTicketService` falls back when no `user_token` is provided)
- Registration: Add `from app.routers.X import router as X_router` + `app.include_router(X_router, tags=["X"])` in `fast_api_app.py`
- Pydantic models: Use `Literal` types for enum fields (e.g., `Literal["low", "normal", "high", "urgent"]`)
- Pagination: All list endpoints accept `limit: int = 20` and `offset: int = 0` query params
- Build gate: Run `next build` after each phase that touches frontend files

---

## Phase 0: Reusable UI Components (Prerequisite)

**Rationale:** Build error/empty/loading components first so all subsequent phases can use them immediately.

### 0a. `DashboardSkeleton` Component

Create `frontend/src/components/ui/DashboardSkeleton.tsx`:
- Animated pulse placeholders matching premium card layout (rounded-[28px])
- Configurable: `rows`, `columns`, `showMetricCards` props
- Uses same shadow/radius tokens as MetricCard

### 0b. `EmptyState` Component

Create `frontend/src/components/ui/EmptyState.tsx`:
- Props: `icon: LucideIcon`, `title: string`, `description: string`, `actionLabel?: string`, `onAction?: () => void`
- Premium styling: centered layout, rounded-[28px] dashed border, gradient icon background

### 0c. `DashboardErrorBoundary` Component

Create `frontend/src/components/ui/DashboardErrorBoundary.tsx`:
- React error boundary with "Something went wrong" card
- Retry button that resets the error state
- Premium styling matching the design system

---

## Phase 1: Support Vertical Integration

**Rationale:** `SupportTicketService` already has full CRUD in `app/services/support_ticket_service.py`. Only the DB table, router, and frontend wiring are missing.

### 1a. Database Migration

Create `supabase/migrations/YYYYMMDDHHMMSS_create_support_tickets.sql`:

```sql
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'open', 'in_progress', 'waiting', 'resolved', 'closed')),
    assigned_to TEXT,
    resolution TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: users can CRUD their own tickets
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tickets"
    ON public.support_tickets FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own tickets"
    ON public.support_tickets FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tickets"
    ON public.support_tickets FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tickets"
    ON public.support_tickets FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role full access"
    ON public.support_tickets FOR ALL
    USING (auth.role() = 'service_role');

-- Performance indexes
CREATE INDEX idx_support_tickets_user_status ON public.support_tickets(user_id, status);
CREATE INDEX idx_support_tickets_priority ON public.support_tickets(priority);

-- Auto-update updated_at
CREATE TRIGGER set_support_tickets_updated_at
    BEFORE UPDATE ON public.support_tickets
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

### 1b. FastAPI Router

Create `app/routers/support.py`:

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/support/tickets` | Create ticket | |
| GET | `/support/tickets` | List tickets | Filter: `status`, `priority`, `assigned_to`. Paginate: `limit`, `offset` |
| GET | `/support/tickets/{id}` | Get single ticket | |
| PATCH | `/support/tickets/{id}` | Update ticket | Fields: `status`, `priority`, `assigned_to`, `resolution` |
| DELETE | `/support/tickets/{id}` | Delete ticket | |

Register in `fast_api_app.py` with `tags=["Support"]`.

### 1c. Frontend Service

Create `frontend/src/services/support.ts` with `fetchWithAuth` calls matching the router endpoints.

### 1d. Wire Support Page

Update `frontend/src/app/dashboard/support/page.tsx`:
- Replace local `useState` ticket arrays with `useEffect` -> `supportService.listTickets()`
- Wire "Submit Ticket" form to `supportService.createTicket()`
- Wire status changes to `supportService.updateTicket()`
- Use `DashboardSkeleton` for loading, `EmptyState` for no tickets, `DashboardErrorBoundary` wrapper

---

## Phase 2: Brain Dump Premium Polish

**Rationale:** Single-file change, high visual impact. The `BrainDumpInterface` component is already functional.

### Changes to `frontend/src/app/dashboard/braindump/page.tsx`:
- Wrap in `PremiumShell` instead of `PersonaDashboardLayout`
- Add `motion.div` entry animation
- Apply premium design tokens to the container

---

## Phase 3: Settings Premium + Backend Wiring

### 3a. Settings Page (`/settings/page.tsx`)

Path: `frontend/src/app/settings/page.tsx` (NOT under `/dashboard/`)

- Wrap in `PremiumShell`
- Read profile data from `users_profile` table on mount via Supabase client
- Wire "Save Changes" button to upsert into `users_profile` table
- Apply premium design tokens (rounded-[28px] sections, shadows, styled inputs)

### 3b. Integrations Page (`/settings/integrations/page.tsx`)

Path: `frontend/src/app/settings/integrations/page.tsx`

- Create a new backend endpoint `POST /configuration/test-connection` in `app/routers/configuration.py` that validates credentials for a given integration type
- Replace `Math.random()` mock connection test with real call to the new endpoint
- Wire the setup wizard's "Save & Activate" to persist via `/configuration/save-api-key` (already exists)
- Apply premium design tokens to card layout and modals

---

## Phase 4: Learning Hub Vertical Integration

### 4a. Database Migration

Create `supabase/migrations/YYYYMMDDHHMMSS_create_learning_tables.sql`:

```sql
CREATE TABLE IF NOT EXISTS public.learning_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'beginner'
        CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    duration_minutes INT NOT NULL DEFAULT 30,
    lessons_count INT NOT NULL DEFAULT 1,
    thumbnail_gradient TEXT,
    is_recommended BOOLEAN NOT NULL DEFAULT false,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.learning_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.learning_courses(id) ON DELETE CASCADE,
    progress_percent INT NOT NULL DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (status IN ('not_started', 'in_progress', 'completed')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, course_id)
);
```

RLS policies:
- `learning_courses`: Public read (all authenticated users), service_role write
- `learning_progress`: User CRUD own rows, service_role full access

Seed with 6-10 courses covering Pikar-AI features.

### 4b. FastAPI Router

Create `app/routers/learning.py`:

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/learning/courses` | List courses | Filter: `category`. Paginate: `limit`, `offset` |
| GET | `/learning/courses/{id}` | Get course detail | |
| GET | `/learning/progress` | Get user's progress | Joins with courses for full data |
| POST | `/learning/progress/{course_id}/start` | Start a course | Sets `status='in_progress'`, `started_at=now()` |
| PATCH | `/learning/progress/{course_id}` | Update progress | Sets `progress_percent`, auto-completes at 100 |

### 4c. Frontend Service + Page Wiring

Create `frontend/src/services/learning.ts`. Wire Learning Hub page to fetch real courses and track real progress. Use Phase 0 components for loading/empty/error states.

---

## Phase 5: Community Vertical Integration

### 5a. Database Migration

Create `supabase/migrations/YYYYMMDDHHMMSS_create_community_tables.sql`:

```sql
CREATE TABLE IF NOT EXISTS public.community_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL DEFAULT 'Anonymous',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    tags TEXT[] DEFAULT '{}',
    upvotes INT NOT NULL DEFAULT 0,
    reply_count INT NOT NULL DEFAULT 0,
    is_pinned BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.community_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.community_posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL DEFAULT 'Anonymous',
    body TEXT NOT NULL,
    upvotes INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Upvote tracking to prevent duplicates
CREATE TABLE IF NOT EXISTS public.community_upvotes (
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES public.community_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, post_id)
);
```

RLS policies:
- `community_posts`: Public read (all authenticated users), user can create/update/delete own posts
- `community_comments`: Public read, user can create/delete own comments
- `community_upvotes`: User can insert/delete own upvotes (toggle pattern)

### 5b. FastAPI Router

Create `app/routers/community.py`:

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/community/posts` | List posts | Filter: `category`, sort: `recent`/`popular`. Paginate: `limit`, `offset` |
| POST | `/community/posts` | Create post | |
| GET | `/community/posts/{id}` | Get post with comments | |
| POST | `/community/posts/{id}/comments` | Add comment | Increments `reply_count` |
| POST | `/community/posts/{id}/upvote` | Toggle upvote | Insert/delete in `community_upvotes`, increment/decrement counter |

### 5c. Frontend Service + Page Wiring

Create `frontend/src/services/community.ts`. Wire Community page to real data. Use Phase 0 components for loading/empty/error states.

---

## Phase 6: Consistency Pass

Sweep all 18 dashboard pages to ensure:
- Loading state uses `DashboardSkeleton`
- Empty state uses `EmptyState` component
- Error state uses `DashboardErrorBoundary` wrapper
- Consistent `PremiumShell` or `PersonaDashboardLayout` wrapper
- Run `next build` to verify all routes compile

---

## Deferred Phases

### Phase 7: Stripe Connect (User Payment Receiving)
Users connect their own Stripe accounts to receive payments from their customers. Uses Stripe Connect Standard or Express. **Deferred until app is feature-complete.**

### Phase 8: Pikar-AI Subscriptions (User Billing)
Users pay for Pikar-AI tiers (free/pro/enterprise). **Deferred until app is ready for real users.**

---

## Success Criteria

- All 18 dashboard pages reach premium quality level
- Learning, Support, Community pages persist data to Supabase
- Settings page reads/writes real user profile data
- No page uses mock data or `Math.random()` for business logic
- All pages have loading, empty, and error states
- `next build` compiles all routes without errors
- Backend tests pass for new routers
