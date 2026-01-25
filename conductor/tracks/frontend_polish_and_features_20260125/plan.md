# Implementation Plan: Frontend Polish & Features

## Standards & Guidelines
**CRITICAL:** All tasks in this plan must adhere to the following standards defined in `conductor/tech-stack.md` and `conductor/workflow.md`:
1.  **Systematic Debugging:** Use the 4-phase protocol for *any* issue. No random fixes.
2.  **Frontend:** Apply `react-modernization` (Hooks, Concurrent features) and `vercel-react-best-practices` (No waterfalls, optimal bundles).
3.  **Backend:** Ensure all Supabase interactions follow `supabase-best-practices` (RLS, Security).
4.  **Visuals:** Use `frontend-design` and `ui-ux-pro-max` principles.

## Phase 1: Authentication & Settings [checkpoint: ]

- [x] **Task: Forgot Password Page** 6ef5f86
    - Create `src/app/auth/forgot-password/page.tsx` with Supabase `resetPasswordForEmail`.
- [x] **Task: Reset Password Page** 010912b
    - Create `src/app/auth/reset-password/page.tsx` with `updateUser`.
- [x] **Task: Update Auth Navigation** 678c7b0
    - Add "Forgot Password?" link to Login.
    - Add "Don't have an account?" / "Already have an account?" links.
- [x] **Task: Persona-Aware Settings** 8d38d96
    - Update `src/app/settings/page.tsx` to display different sections based on user role (mocked or from context).
- [ ] **Task: Conductor - User Manual Verification**

## Phase 2: Dynamic Workflow Generator [checkpoint: ]

- [ ] **Task: Dynamic Generator UI**
    - Create `src/components/workflow/DynamicWorkflowGenerator.tsx`.
    - Interface: Textarea for prompt + "Generate" button + Visual Result placeholder (or reuse `WorkflowBuilder` in read-only mode).
- [ ] **Task: Integration**
    - Add this component to a new route `src/app/workflows/generate/page.tsx`.
- [ ] **Task: Conductor - User Manual Verification**

## Phase 3: Persona Dashboards [checkpoint: ]

- [ ] **Task: Solopreneur Dashboard**
    - Implement specific widgets (KPIs, Task List) in `src/app/(personas)/solopreneur/page.tsx`.
- [ ] **Task: Startup Dashboard**
    - Implement specific widgets (Burn Rate, Roadmap) in `src/app/(personas)/startup/page.tsx`.
- [ ] **Task: SME/Enterprise Dashboards**
    - Implement specific widgets (Depts, Security) in remaining pages.
- [ ] **Task: Conductor - User Manual Verification**

## Phase 4: Final Polish & Routing [checkpoint: ]

- [ ] **Task: Landing Page Component**
    - Ensure `ThreeBackground.tsx` exists and works (create if missing).
- [ ] **Task: Routing Verification**
    - Walkthrough of the user journey (Landing -> Signup -> Onboarding -> Dashboard).
    - Fix any broken links.
- [ ] **Task: Conductor - User Manual Verification**
