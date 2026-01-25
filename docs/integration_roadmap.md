# Pikar AI Integration Roadmap

This document defines the connecting tissue between the React Frontend (Next.js) and the Backend Infrastructure (Supabase + FastAPI).

## 1. Architecture Overview

- **Frontend**: Next.js 14 (App Router)
- **Database/Auth**: Supabase (PostgreSQL + GoTrue)
- **Agent Runtime**: Python FastAPI (Google ADK)

## 2. Integration Points

### A. Authentication (Completed by default)
- **Mechanism**: Supabase Auth (Email/Password + OAuth).
- **Frontend**: `@supabase/ssr` (Next.js Auth Helpers).
- **Backend compatibility**: RLS policies in `0003_complete_schema.sql` already use `auth.uid()`. **Verified.**

### B. Business Data (CRUD)
- **Mechanism**: Direct Supabase Client calls from Frontend (Server Components & Client Hooks).
- **Policy**: Frontend MUST NOT use a custom backend API for CRUD. It MUST query Supabase directly.
- **Tables to Map**:
    - `initiatives` (Strategy Dashboard)
    - `campaigns` (Marketing Dashboard)
    - `recruitment_jobs` (HR Dashboard)
    - `support_tickets` (Support Dashboard)
    - `compliance_risks` (Legal Dashboard)

### C. Agent Interaction (The "Chat")
- **Current State**: Backend exposes `A2A` (Agent-to-Agent) protocol.
- **Gap**: Frontend cannot easily speak "A2A".
- **Solution: The "Agent Gateway" Edge Function**
    - We will create a Supabase Edge Function `chat-gateway`.
    - **Frontend** POSTs message to `functions/v1/chat-gateway`.
    - **Edge Function** validates User Auth.
    - **Edge Function** forwards request to FastAPI Agent Server (or invokes Agent logic directly if compiled to Wasm/Edge - *likely forwarding to Python container*).
    - ** Alternative**: Use Supabase Realtime for "Chat". User inserts into `chat_messages` table -> Python backend listens to INSERT -> Processes -> Updates row.

## 3. Step-by-Step Integration Plan

### Phase 1: Type Synchronization
- [ ] **Generate Types**: Run `supabase gen types typescript` against the live DB schema.
- [ ] **Sync**: Save to `frontend_starter/types/supabase.ts`.

### Phase 2: Auth Unification
- [ ] **Env Sync**: Ensure Frontend `.env` has the same `NEXT_PUBLIC_SUPABASE_URL` as the Backend's.
- [ ] **Middleware**: Configure `middleware.ts` in Next.js to protect Dashboard routes.

### Phase 3: Client-Side Data Fetching
- [ ] **Hooks**: Create `useInitiatives`, `useCampaigns` hooks using the generated types.

### Phase 4: Agent Chat Pipeline (The Critical Path)
- [ ] **Decision**: We will use **Supabase Realtime** for the Chat Interface to ensure compatibility.
- [ ] **Schema Action**: Create `agent_messages` table (if not exists).
- [ ] **Backend Listener**: Ensure Python Backend has a listener (or polling) for new messages (This might be a missing piece in `app/`).
- *Refinement*: If Realtime is too complex for now, we will stick to a simple HTTP Proxy to FastAPI.

## 4. Immediate Next Steps for Frontend
1.  Run `npx supabase gen types` to get the schema.
2.  Install `@supabase/ssr` in `frontend_starter`.
3.  Configure `provider` for Supabase.
