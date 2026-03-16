# Remaining Pages Polish Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish all remaining unpolished dashboard pages to match the premium design language established in content, finance, and reports pages — consistent MetricCards, gradient icon headers, staggered motion animations, PremiumShell wrapping, DashboardErrorBoundary, and Breadcrumb navigation.

**Architecture:** Group pages into 5 logical chunks. Each chunk polishes 2-4 related pages sharing similar patterns. Use the existing `MetricCard`, `PremiumShell`, `DashboardErrorBoundary`, and `Breadcrumb` components — NO new shared components needed. Replace all `@heroicons` imports with `lucide-react` for icon consistency. Each task produces a buildable, committable unit.

**Import conventions:**
- `PremiumShell`: use default import (`import PremiumShell from '...'`) for workflow pages that already import it that way; use named import (`import { PremiumShell } from '...'`) for pages that already use it that way. Both work — keep whichever the file already uses.
- `DashboardErrorBoundary`: always default import
- `Breadcrumb`: always named import `{ Breadcrumb }`
- `MetricCard`: always default import
- Icons: always `lucide-react` (never `@heroicons`)
- `sonner`: `<Toaster>` is already mounted in the root layout — just import `{ toast }`

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4, framer-motion 12, lucide-react

---

## Design Token Reference

| Token | Current (Unpolished) | Target (Premium) |
|-------|---------------------|-----------------|
| Card radius | `rounded-2xl` / `rounded-3xl` | `rounded-[28px]` |
| Card shadow | `shadow-sm` / `shadow-md` | `shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)]` |
| Section shadow | `shadow-sm` | `shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]` |
| Hover shadow | `hover:shadow-md` | `hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]` |
| List item shadow | none / `shadow-sm` | `shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)]` |
| Eyebrow text | `text-xs` | `text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400` |
| Entry animation | none or `{ opacity: 0, y: 10 }` | `initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay, ease: [0.21, 0.47, 0.32, 0.98] }}` |
| Border | `border border-slate-100` / `border-slate-200` | `border border-slate-100/80` |
| Icon library | mixed `@heroicons` + `lucide-react` | `lucide-react` only |
| Page structure | varies | `DashboardErrorBoundary > PremiumShell > motion.div.mx-auto.max-w-7xl.p-6` |

---

## Chunk 1: Workflow Pages (Templates + Active + Completed)

These three pages share the most code and patterns. They all currently use `@heroicons`, lack motion animations, lack gradient headers, and show raw JSON context.

---

### Task 1: Polish Workflow Templates Page

**Files:**
- Modify: `frontend/src/app/dashboard/workflows/templates/page.tsx`

**Current state:** Already has `PremiumShell` (default import, line 7). Does NOT have `DashboardErrorBoundary`, `Breadcrumb`, `motion`, or gradient header. Uses `@heroicons` icons.

**What changes:**
- Replace `@heroicons` with `lucide-react` equivalents (`MagnifyingGlassIcon` -> `Search`, `XMarkIcon` -> `X`)
- Wrap existing `<PremiumShell>` with `<DashboardErrorBoundary>` (do NOT add a second PremiumShell)
- Add `Breadcrumb` navigation
- Add `motion` import and staggered page animation
- Add gradient icon header (Workflow icon with blue gradient)
- Replace raw modal with premium modal styling (rounded-[28px], backdrop-blur, motion animation)
- Add `LoadingSkeleton` function using `rounded-[28px]` cards

- [ ] **Step 1: Replace icon imports and add missing imports**

```typescript
// REMOVE this line:
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';

// ADD these lines (keep existing PremiumShell default import):
import { Search, X, Workflow, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
```

- [ ] **Step 2: Wrap existing PremiumShell with DashboardErrorBoundary, add breadcrumb and gradient header**

The page currently returns `<PremiumShell>...<div className="max-w-7xl mx-auto px-4 ...">`. Change to:

```typescript
return (
  <DashboardErrorBoundary fallbackTitle="Workflow Templates Error">
    <PremiumShell>
      <motion.div
        className="mx-auto max-w-7xl p-6"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-4">
          <Breadcrumb items={[
            { label: 'Home', href: '/dashboard' },
            { label: 'Workflows', href: '/dashboard/workflows/templates' },
            { label: 'Templates' },
          ]} />
        </div>

        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-400 to-indigo-500 shadow-lg shadow-blue-200">
              <Workflow className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                Workflow Templates
              </h1>
              <p className="mt-0.5 text-sm text-slate-500">
                Choose from our library of verified templates to automate your repetitive tasks.
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push('/dashboard/workflows/editor/new')}
            className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700"
          >
            <Plus className="h-4 w-4" />
            Create Draft
          </button>
        </div>
        {/* ... rest of page content (filters, grid, etc.) stays the same ... */}
      </motion.div>
    </PremiumShell>
  </DashboardErrorBoundary>
);
```

**Important:** Remove the old `<PremiumShell>` and `<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">` wrapper — they are replaced by the above.

- [ ] **Step 3: Add LoadingSkeleton and upgrade empty/error states**

Add above the component:
```typescript
function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-12 w-64 rounded-xl bg-slate-100" />
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-10 w-24 rounded-full bg-slate-100" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-64 rounded-[28px] bg-slate-100" />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Replace icon references in JSX (`MagnifyingGlassIcon` -> `Search`, `XMarkIcon` -> `X`)**

Find and replace all `MagnifyingGlassIcon` with `Search` and `XMarkIcon` with `X` in the JSX. Update className props (`className="h-4 w-4"` for lucide).

- [ ] **Step 5: Upgrade the modal to premium styling**

Replace the modal section with:
```typescript
<AnimatePresence>
  {isModalOpen && selectedTemplate && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        className="w-full max-w-lg rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
      >
        {/* Modal header */}
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Start Workflow</h3>
          <button onClick={() => setIsModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-4">
          Starting <span className="font-semibold text-slate-700">{selectedTemplate.name}</span>. Provide context below.
        </p>
        <label className="block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-2">
          Topic / Context (Optional)
        </label>
        <input
          type="text"
          className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
          placeholder="e.g. Q4 Marketing Strategy"
          value={workflowTopic}
          onChange={(e) => setWorkflowTopic(e.target.value)}
        />
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={() => setIsModalOpen(false)}
            className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirmStart}
            disabled={starting}
            className="px-5 py-2.5 rounded-xl bg-teal-600 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            {starting ? 'Starting...' : 'Start Workflow'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )}
</AnimatePresence>
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && npx next build`
Expected: Build succeeds with no errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/dashboard/workflows/templates/page.tsx
git commit -m "polish(workflows): upgrade templates page to premium design language"
```

---

### Task 2: Polish Active Workflows Page

**Files:**
- Modify: `frontend/src/app/dashboard/workflows/active/page.tsx`

**Current state:** Already has `PremiumShell` (default import, line 4). Does NOT have `DashboardErrorBoundary`, `Breadcrumb`, or `motion`. Uses `@heroicons` icons. Shows raw `JSON.stringify` for context data.

**What changes:**
- Replace `@heroicons` with `lucide-react` (`ArrowPathIcon` -> `RefreshCw`, `XMarkIcon` -> `X`, `PlusIcon` -> `Plus`)
- Wrap existing `<PremiumShell>` with `<DashboardErrorBoundary>` (do NOT add a second PremiumShell)
- Add `Breadcrumb`, `motion`
- Add gradient icon header (Play icon with emerald gradient)
- Replace raw `JSON.stringify` context display with a formatted key-value card

- [ ] **Step 1: Replace icon imports and add missing imports**

```typescript
// REMOVE this line:
import { ArrowPathIcon, XMarkIcon, PlusIcon } from '@heroicons/react/24/outline';

// ADD these lines (keep existing PremiumShell default import):
import { RefreshCw, X, Plus, Play } from 'lucide-react';
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
```

- [ ] **Step 2: Wrap existing PremiumShell with DashboardErrorBoundary and add gradient header**

Replace the current `return (<PremiumShell>...<div className="max-w-7xl...">` with:
```typescript
return (
  <DashboardErrorBoundary fallbackTitle="Active Workflows Error">
    <PremiumShell>
      <motion.div
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-64px)] flex flex-col"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-4">
          <Breadcrumb items={[
            { label: 'Home', href: '/dashboard' },
            { label: 'Workflows', href: '/dashboard/workflows/templates' },
            { label: 'Active' },
          ]} />
        </div>

        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 shadow-lg shadow-emerald-200">
              <Play className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Active Workflows</h1>
              <p className="mt-0.5 text-sm text-slate-500">Monitor and manage your running processes.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push('/dashboard/workflows/templates')}
              className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700"
            >
              <Plus className="h-4 w-4" />
              New Workflow
            </button>
            <button
              onClick={fetchExecutions}
              className="p-2.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors"
            >
              <RefreshCw className="h-5 w-5" />
            </button>
          </div>
        </div>
```

- [ ] **Step 3: Replace raw JSON context display with formatted card**

Replace the `JSON.stringify` pre block:
```typescript
{/* Context Data - formatted */}
<div className="rounded-[28px] border border-slate-100/80 bg-slate-50/50 p-5">
  <h3 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-3">Context</h3>
  <div className="space-y-2">
    {Object.entries(detailsContext).map(([key, val]) => (
      <div key={key} className="flex items-start gap-3 text-sm">
        <span className="text-slate-400 font-medium min-w-[100px] capitalize">{key.replace(/_/g, ' ')}</span>
        <span className="text-slate-700">{typeof val === 'string' ? val : JSON.stringify(val)}</span>
      </div>
    ))}
    {Object.keys(detailsContext).length === 0 && (
      <p className="text-sm text-slate-400 italic">No context provided</p>
    )}
  </div>
</div>
```

- [ ] **Step 4: Replace all `@heroicons` icon usages in JSX**

- `<PlusIcon className="w-5 h-5 mr-2" />` -> `<Plus className="h-5 w-5 mr-2" />`
- `<ArrowPathIcon className="w-5 h-5" />` -> `<RefreshCw className="h-5 w-5" />`
- `<XMarkIcon className="w-6 h-6" />` -> `<X className="h-6 w-6" />`

- [ ] **Step 5: Close the DashboardErrorBoundary wrapper**

Add closing tags:
```typescript
      </motion.div>
    </PremiumShell>
  </DashboardErrorBoundary>
);
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && npx next build`
Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/dashboard/workflows/active/page.tsx
git commit -m "polish(workflows): upgrade active workflows page to premium design"
```

---

### Task 3: Polish Completed Workflows Page

**Files:**
- Modify: `frontend/src/app/dashboard/workflows/completed/page.tsx`

**Current state:** Already has `PremiumShell` (default import, line 4). Does NOT have `DashboardErrorBoundary`, `Breadcrumb`, or `motion`. Uses `@heroicons` icons. Shows raw `JSON.stringify` for context data.

**What changes:**
- Same pattern as active page: replace `@heroicons` -> `lucide-react`, wrap existing PremiumShell with error boundary (don't nest), add breadcrumb, gradient header, motion animation, formatted context display
- Add gradient icon header (History with slate gradient for "history" feel)

- [ ] **Step 1: Replace icon imports and add missing imports**

```typescript
// REMOVE:
import { ChevronLeftIcon, ChevronRightIcon, XMarkIcon } from '@heroicons/react/24/outline';

// ADD:
import { ChevronLeft, ChevronRight, X, CheckCircle2, History } from 'lucide-react';
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
```

- [ ] **Step 2: Add DashboardErrorBoundary wrapper, breadcrumb, and gradient header**

Same pattern as active page, but with:
```typescript
<div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-400 to-slate-600 shadow-lg shadow-slate-200">
  <History className="h-6 w-6 text-white" />
</div>
<div>
  <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Completed Workflows</h1>
  <p className="mt-0.5 text-sm text-slate-500">History of all your finished processes.</p>
</div>
```

- [ ] **Step 3: Replace raw JSON context display with formatted card**

Same formatted context card pattern as Task 2 Step 3.

- [ ] **Step 4: Replace all `@heroicons` icon usages in JSX**

- `<ChevronLeftIcon>` -> `<ChevronLeft>`
- `<ChevronRightIcon>` -> `<ChevronRight>`
- `<XMarkIcon>` -> `<X>`

- [ ] **Step 5: Verify build**

Run: `cd frontend && npx next build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/dashboard/workflows/completed/page.tsx
git commit -m "polish(workflows): upgrade completed workflows page to premium design"
```

---

### Task 4: Polish Generate Workflow Page

**Files:**
- Modify: `frontend/src/app/dashboard/workflows/generate/page.tsx`

**Current state:** Already has `PremiumShell` (default import, line 4). Does NOT have `DashboardErrorBoundary`, `Breadcrumb`, or `motion`. Uses `@heroicons/react/24/solid` SparklesIcon. Already has a centered icon header (purple bg, but not gradient).

**What changes:**
- Replace `@heroicons/react/24/solid` SparklesIcon with `lucide-react` Sparkles
- Wrap existing `<PremiumShell>` with `<DashboardErrorBoundary>` (don't nest)
- Add `Breadcrumb`, `motion`
- Upgrade icon header to gradient style

- [ ] **Step 1: Replace imports**

```typescript
// REMOVE this line:
import { SparklesIcon } from '@heroicons/react/24/solid';

// ADD these lines (keep existing PremiumShell default import):
import { Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
```

- [ ] **Step 2: Wrap existing PremiumShell with DashboardErrorBoundary, add breadcrumb, upgrade header**

Replace the current `return (<PremiumShell>...<div className="max-w-3xl...">` with:
```typescript
return (
  <DashboardErrorBoundary fallbackTitle="Generate Workflow Error">
    <PremiumShell>
      <motion.div
        className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-6">
          <Breadcrumb items={[
            { label: 'Home', href: '/dashboard' },
            { label: 'Workflows', href: '/dashboard/workflows/templates' },
            { label: 'Generate' },
          ]} />
        </div>

        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-400 to-purple-500 p-3 shadow-lg shadow-purple-200 mb-4">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Generate with AI</h1>
          <p className="mt-2 text-lg text-slate-500">
            Describe your process, and our AI will design a custom workflow for you in seconds.
          </p>
        </div>
        {/* ... rest of page content (form, info box, result) stays the same ... */}
      </motion.div>
    </PremiumShell>
  </DashboardErrorBoundary>
);
```

**Important:** Remove the old `<PremiumShell>` and `<div className="max-w-3xl mx-auto...">` wrapper — they are replaced.

- [ ] **Step 3: Replace all `SparklesIcon` with `Sparkles` in JSX**

Find and replace throughout the file.

- [ ] **Step 4: Upgrade form card and info box to premium radius**

Change `rounded-3xl` -> `rounded-[28px]` and `rounded-2xl` -> `rounded-[28px]` on the form and info containers. Add premium shadow.

- [ ] **Step 5: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/dashboard/workflows/generate/page.tsx
git commit -m "polish(workflows): upgrade generate page to premium design"
```

---

### Task 5: Polish Workflow Editor Page

**Files:**
- Modify: `frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx`

**Current state:** Already has `PremiumShell` (default import, line 5). Does NOT have `DashboardErrorBoundary`, `Breadcrumb`, or `motion`. Uses `@heroicons` icons.

**What changes:**
- Replace `@heroicons` with `lucide-react`
- Wrap existing `<PremiumShell>` with `<DashboardErrorBoundary>` (don't nest)
- Add `Breadcrumb`, `motion`
- Add gradient icon header
- Upgrade form sections to premium card styling

- [ ] **Step 1: Replace imports**

```typescript
// REMOVE:
import { ArrowPathIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';

// ADD:
import { RefreshCw, Plus, Trash2, Pencil } from 'lucide-react';
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
```

- [ ] **Step 2: Wrap in DashboardErrorBoundary, add breadcrumb and gradient header**

```typescript
<div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-blue-500 shadow-lg shadow-indigo-200">
  <Pencil className="h-6 w-6 text-white" />
</div>
```

- [ ] **Step 3: Replace all `@heroicons` usages in JSX**

- `<PlusIcon>` -> `<Plus>`
- `<TrashIcon>` -> `<Trash2>`
- `<ArrowPathIcon>` -> `<RefreshCw>`

- [ ] **Step 4: Upgrade form section cards to premium styling**

Wrap each phase section in: `rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]`

- [ ] **Step 5: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/dashboard/workflows/editor/\[templateId\]/page.tsx
git commit -m "polish(workflows): upgrade editor page to premium design"
```

---

## Chunk 2: Initiative Pages (List + Detail + New)

These three pages already have `PremiumShell`, `DashboardErrorBoundary`, `Breadcrumb`, `motion`, and `lucide-react` icons. The remaining work is **incremental upgrades only**: replacing inline metric blocks with `MetricCard`, adding gradient icon headers, and upgrading card radius/shadow to premium tokens.

---

### Task 6: Polish Initiatives List Page (Incremental)

**Files:**
- Modify: `frontend/src/app/dashboard/initiatives/page.tsx`

**Current state:** Already has `DashboardErrorBoundary`, `PremiumShell`, `Breadcrumb`, `motion`, `AnimatePresence`, and all `lucide-react` icons. Uses inline colored metric divs and `rounded-2xl` card styling.

**What changes (incremental only):**
- Add `MetricCard` import and replace inline metrics grid with `MetricCard` components
- Add gradient icon header (Target icon with teal gradient) before the existing `<h1>`
- Upgrade initiative list cards to premium shadow/radius

- [ ] **Step 1: Add MetricCard import and add gradient icon to existing header**

Add import:
```typescript
import MetricCard from '@/components/ui/MetricCard';
```

The page already has `Target` imported. Find the existing header `<div>` containing the `<h1>Initiatives</h1>` and add a gradient icon before the text:
```typescript
{/* Replace the existing header <div> that has <h1> and <p> */}
<div className="flex items-center justify-between">
  <div className="flex items-center gap-4">
    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 shadow-lg shadow-teal-200">
      <Target className="h-6 w-6 text-white" />
    </div>
    <div>
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Initiatives</h1>
      <p className="mt-0.5 text-sm text-slate-500">Track your strategic projects through the 5-phase framework</p>
    </div>
  </div>
  {/* Keep existing "New Initiative" button as-is */}
</div>
```

- [ ] **Step 2: Replace inline metrics with MetricCard grid**

Replace the metrics grid:
```typescript
<div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
  <MetricCard label="Total" value={metrics.total} icon={Target} gradient="from-slate-400 to-slate-600" delay={0} />
  <MetricCard label="In Progress" value={metrics.in_progress} icon={Clock} gradient="from-blue-400 to-indigo-500" delay={0.05} />
  <MetricCard label="Completed" value={metrics.completed} icon={CheckCircle2} gradient="from-emerald-400 to-teal-500" delay={0.1} />
  <MetricCard label="Blocked" value={metrics.blocked} icon={AlertTriangle} gradient="from-rose-400 to-red-500" delay={0.15} />
</div>
```

- [ ] **Step 3: Upgrade initiative list item cards to premium shadows**

Replace card className:
```
// FROM:
"bg-white rounded-2xl p-5 border border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200 transition-all cursor-pointer group"

// TO:
"bg-white rounded-[28px] p-5 border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5 transition-all cursor-pointer group"
```

- [ ] **Step 4: Upgrade empty state card**

```
// FROM:
"bg-white p-12 rounded-3xl border border-slate-100 shadow-sm"

// TO:
"bg-white p-12 rounded-[28px] border border-dashed border-slate-200"
```

- [ ] **Step 5: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/dashboard/initiatives/page.tsx
git commit -m "polish(initiatives): upgrade list page with MetricCards and premium design"
```

---

### Task 7: Polish Initiatives Detail Page

**Files:**
- Modify: `frontend/src/app/dashboard/initiatives/[id]/page.tsx`

**What changes:**
- Add gradient icon header
- Upgrade section cards to premium `rounded-[28px]` with premium shadows
- Upgrade section headers to eyebrow style (`text-[11px] uppercase tracking-[0.28em]`)
- Add `motion.div` wrapper for page-level animation
- This is a 1018-line file — changes are CSS-class-level upgrades, not structural

- [ ] **Step 1: Add motion import and wrap return in motion.div**

Add `import { motion } from 'framer-motion';` if not present.

Wrap the top-level content div:
```typescript
<motion.div
  initial={{ opacity: 0, y: 18 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
>
```

- [ ] **Step 2: Add gradient icon header at top of page**

```typescript
<div className="flex items-center gap-4 mb-6">
  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 shadow-lg shadow-teal-200">
    <Target className="h-6 w-6 text-white" />
  </div>
  <div className="flex-1 min-w-0">
    <h1 className="text-3xl font-semibold tracking-tight text-slate-900 truncate">{initiative.title}</h1>
    <p className="mt-0.5 text-sm text-slate-500">{initiative.description}</p>
  </div>
</div>
```

- [ ] **Step 3: Upgrade all section card containers**

Find all instances of `rounded-2xl` or `rounded-3xl` on white bg section cards and replace with:
```
rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]
```

- [ ] **Step 4: Upgrade section headers to eyebrow style**

Replace patterns like `text-lg font-semibold text-slate-800` on section titles within cards with:
```
text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400
```

- [ ] **Step 5: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/dashboard/initiatives/\[id\]/page.tsx
git commit -m "polish(initiatives): upgrade detail page to premium design"
```

---

### Task 8: Polish New Initiative Page

**Files:**
- Modify: `frontend/src/app/dashboard/initiatives/new/page.tsx`

**What changes:**
- Add gradient icon header (Lightbulb with amber gradient)
- Upgrade template cards to premium radius/shadow
- Add `motion.div` page animation
- Upgrade wizard step cards

- [ ] **Step 1: Add motion wrapper and gradient icon header**

```typescript
<div className="flex items-center gap-4 mb-6">
  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-200">
    <Lightbulb className="h-6 w-6 text-white" />
  </div>
  <div>
    <h1 className="text-3xl font-semibold tracking-tight text-slate-900">New Initiative</h1>
    <p className="mt-0.5 text-sm text-slate-500">Choose a template or start from scratch</p>
  </div>
</div>
```

- [ ] **Step 2: Upgrade template selection cards to premium styling**

Change card radius to `rounded-[28px]` and add premium shadow.

- [ ] **Step 3: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/dashboard/initiatives/new/page.tsx
git commit -m "polish(initiatives): upgrade new initiative page to premium design"
```

---

## Chunk 3: Brain Dump + User Journeys

---

### Task 9: Fix Brain Dump Interface (remove duplicate header + responsive layout)

**Files:**
- Modify: `frontend/src/components/braindump/BrainDumpInterface.tsx`

**What changes:**
- Remove the duplicate `<h1>Brain Dumps</h1>` header (lines 222-225) since `page.tsx` already renders a gradient header
- Replace hardcoded `w-[30%]` with responsive flexbox
- Replace `any` type in error handler with `unknown`
- Upgrade document list cards and content viewer to premium radius/shadow

- [ ] **Step 1: Remove the duplicate header block**

Remove lines 221-225 (the header block with `<h1>` and description text). The page.tsx wrapper already renders this.

Replace with just the action buttons row:
```typescript
<div className="flex items-center gap-2 mb-6 flex-wrap">
  {/* Sort dropdown */}
  <div className="relative">
    <select ...>
```

- [ ] **Step 2: Replace hardcoded width with responsive flex**

```
// FROM:
<div className="w-[30%] min-w-[280px] flex flex-col gap-4 ...">

// TO:
<div className="w-full md:w-80 lg:w-96 flex-shrink-0 flex flex-col gap-4 ...">
```

- [ ] **Step 3: Fix `any` type in download handler**

```typescript
// FROM:
} catch (error: any) {
    console.error('Download error:', error);
    alert('Error downloading: ' + error.message);

// TO:
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('Download error:', error);
    alert('Error downloading: ' + message);
```

- [ ] **Step 4: Upgrade content viewer card to premium radius**

```
// FROM:
"flex-1 bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100"

// TO:
"flex-1 bg-white rounded-[28px] border border-slate-100/80 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
```

- [ ] **Step 5: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/components/braindump/BrainDumpInterface.tsx
git commit -m "polish(braindump): fix duplicate header, responsive layout, premium styling"
```

---

### Task 10: Polish User Journeys Page (Incremental)

**Files:**
- Modify: `frontend/src/app/dashboard/journeys/page.tsx`

**Current state:** Already has `DashboardErrorBoundary`, `PremiumShell`, `Breadcrumb`, `motion`, `AnimatePresence`, and all `lucide-react` icons. Already has `JourneyCard` component inline with `journey` prop (which includes `persona` field). Uses `alert()` for errors and plain text header without gradient icon.

**What changes (incremental only):**
- Add gradient icon header (Map icon with teal gradient) — replace existing plain `<h1>` header
- Use persona-specific icon colors on journey cards (currently all cards use same `from-teal-50 to-emerald-50` bg — replace with persona-aware gradient)
- Replace `alert()` calls with `toast` from sonner
- Upgrade card styling to premium radius/shadow
- Upgrade outcomes modal to premium styling

- [ ] **Step 1: Add missing import**

```typescript
import { toast } from 'sonner';
```
Note: `<Toaster>` is already mounted in the root layout — just import the function.

- [ ] **Step 2: Add gradient icon header**

Replace the plain header:
```typescript
<div className="flex items-center gap-4">
  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 shadow-lg shadow-teal-200">
    <Map className="h-6 w-6 text-white" />
  </div>
  <div>
    <h1 className="text-3xl font-semibold tracking-tight text-slate-900">User Journeys</h1>
    <p className="mt-0.5 text-sm text-slate-500">
      Browse curated journeys for your business stage. Start any journey as an initiative.
    </p>
  </div>
</div>
```

- [ ] **Step 3: Replace all `alert()` calls with `toast.error()`**

```typescript
// FROM:
alert('Please sign in to create an initiative.');
alert(`Failed to create initiative: ${error.message || 'Please try again.'}`);
alert('Please provide both desired outcomes and a timeline.');

// TO:
toast.error('Please sign in to create an initiative.');
toast.error(`Failed to create initiative: ${error.message || 'Please try again.'}`);
toast.error('Please provide both desired outcomes and a timeline.');
```

- [ ] **Step 4: Use persona-specific gradient icons in JourneyCard**

In the `JourneyCard` component (defined inline at line ~417), `journey.persona` is already available via the `journey` prop. Add a gradient map above the component and replace the existing icon container:

```typescript
// Add this constant ABOVE the JourneyCard function (around line 415):
const PERSONA_GRADIENTS: Record<string, string> = {
  solopreneur: 'from-amber-400 to-orange-500',
  startup: 'from-blue-400 to-indigo-500',
  sme: 'from-purple-400 to-violet-500',
  enterprise: 'from-indigo-400 to-blue-500',
};

// INSIDE JourneyCard, find the icon container (currently line ~438):
// FROM:
<div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-50 to-emerald-50 border border-teal-100 flex items-center justify-center shrink-0">
  <Lightbulb size={16} className="text-teal-600" />
</div>

// TO:
<div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${PERSONA_GRADIENTS[journey.persona] || 'from-teal-400 to-cyan-500'} flex items-center justify-center shrink-0 shadow-sm`}>
  <Lightbulb size={16} className="text-white" />
</div>
```

- [ ] **Step 5: Upgrade journey cards to premium radius/shadow**

```
// FROM:
"bg-white rounded-2xl p-5 border border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200 transition-all"

// TO:
"bg-white rounded-[28px] p-5 border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5 transition-all"
```

- [ ] **Step 6: Upgrade outcomes modal to premium styling**

Replace modal card class:
```
// FROM:
"w-full max-w-xl bg-white rounded-2xl border border-slate-200 shadow-xl p-6"

// TO:
"w-full max-w-xl bg-white rounded-[28px] border border-slate-100/80 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] p-6"
```

- [ ] **Step 7: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/dashboard/journeys/page.tsx
git commit -m "polish(journeys): upgrade to premium design with persona-specific gradients"
```

---

## Chunk 4: Supporting Pages (Settings Integrations)

---

### Task 11: Polish Settings Integrations Page

**Files:**
- Modify: `frontend/src/app/settings/integrations/page.tsx` (at app root, NOT under `/dashboard/`)

**Current state:** Has `DashboardErrorBoundary` but no `PremiumShell`, no `motion`, no gradient header. Uses emoji icons for integrations. Large file (~568 lines).

**What changes:**
- Add `PremiumShell`, `motion` wrapper
- Add gradient icon header (Settings icon with slate gradient)
- Upgrade integration cards to premium radius/shadow

- [ ] **Step 1: Add missing imports**

```typescript
import { motion } from 'framer-motion';
import PremiumShell from '@/components/layout/PremiumShell';
import { Settings } from 'lucide-react';
```

- [ ] **Step 2: Wrap existing `DashboardErrorBoundary` content with PremiumShell > motion.div**

The page already has `DashboardErrorBoundary`. Inside it, wrap with:
```typescript
<DashboardErrorBoundary fallbackTitle="Integrations Error">
  <PremiumShell>
    <motion.div
      className="mx-auto max-w-6xl p-6"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* existing content */}
    </motion.div>
  </PremiumShell>
</DashboardErrorBoundary>
```

- [ ] **Step 3: Add gradient icon header**

```typescript
<div className="flex items-center gap-4 mb-6">
  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-400 to-slate-600 shadow-lg shadow-slate-200">
    <Settings className="h-6 w-6 text-white" />
  </div>
  <div>
    <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Integrations</h1>
    <p className="mt-0.5 text-sm text-slate-500">Connect your favorite tools and services.</p>
  </div>
</div>
```

- [ ] **Step 4: Upgrade integration cards to premium styling**

Apply `rounded-[28px] border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)]` to integration cards.

- [ ] **Step 5: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/settings/integrations/page.tsx
git commit -m "polish(settings): upgrade integrations page to premium design"
```

---

## Chunk 5: Low-Traffic Admin Pages (Departments, Org Chart, Approval, Public Pages)

---

### Task 12: Polish Departments Page

**Files:**
- Modify: `frontend/src/app/departments/page.tsx` (at app root, NOT under `/dashboard/`)

**Current state:** No `PremiumShell`, no `DashboardErrorBoundary`, no `motion`. Uses `lucide-react` icons (Play, Pause, Activity, RefreshCw). Has functional department cards with status indicators and tick/restart buttons. Polls every 5 seconds.

**What changes:**
- Add `PremiumShell`, `DashboardErrorBoundary`, `motion`
- Add gradient icon header (Building2 icon with indigo gradient)
- Upgrade existing department cards to premium radius/shadow styling
- Keep all existing functionality (status toggle, tick, polling)

- [ ] **Step 1: Add imports and wrappers**

```typescript
import { motion } from 'framer-motion';
import PremiumShell from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Building2 } from 'lucide-react'; // add to existing lucide imports
```

Wrap existing return in:
```typescript
<DashboardErrorBoundary fallbackTitle="Departments Error">
  <PremiumShell>
    <motion.div
      className="mx-auto max-w-6xl p-6"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* gradient header + existing content */}
    </motion.div>
  </PremiumShell>
</DashboardErrorBoundary>
```

- [ ] **Step 2: Add gradient icon header and upgrade department cards**

Add header:
```typescript
<div className="flex items-center gap-4 mb-6">
  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-blue-500 shadow-lg shadow-indigo-200">
    <Building2 className="h-6 w-6 text-white" />
  </div>
  <div>
    <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Departments</h1>
    <p className="mt-0.5 text-sm text-slate-500">Real-time status of your AI agent departments.</p>
  </div>
</div>
```

Upgrade card classes to premium tokens: `rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)]`

- [ ] **Step 3: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/departments/page.tsx
git commit -m "polish(departments): upgrade to premium card layout with PremiumShell"
```

---

### Task 13: Polish Org Chart Page

**Files:**
- Modify: `frontend/src/app/org-chart/page.tsx` (at app root, NOT under `/dashboard/`)

**Current state:** No `PremiumShell`, no `DashboardErrorBoundary`, no `motion`. Uses `next/dynamic` to load `OrgChart` component (SSR disabled). Has a basic header bar with badge counts. Full-height layout (`h-screen`).

**What changes:**
- Add `DashboardErrorBoundary` and `motion` wrapper
- Upgrade header bar to premium gradient icon style
- Keep full-height layout and dynamic import (SSR-off is correct for org chart)
- Note: Do NOT wrap in `PremiumShell` — this page uses full-screen layout for the interactive chart, which conflicts with PremiumShell's sidebar.

- [ ] **Step 1: Add imports and error boundary wrapper**

```typescript
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Users } from 'lucide-react';
```

- [ ] **Step 2: Upgrade header bar to premium gradient style**

Replace the existing header bar div:
```typescript
<div className="p-4 bg-white border-b border-slate-100/80 flex justify-between items-center shadow-[0_8px_30px_-15px_rgba(15,23,42,0.1)] z-10">
  <div className="flex items-center gap-3">
    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-400 to-violet-500 shadow-lg shadow-purple-200">
      <Users className="h-5 w-5 text-white" />
    </div>
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-slate-900">Hybrid Workforce</h1>
      <p className="text-sm text-slate-500">Real-time view of your AI Agents and their status</p>
    </div>
  </div>
  <div className="flex gap-2 text-sm">
    <span className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full border border-indigo-100">1 Director</span>
    <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-100">Active Agents</span>
  </div>
</div>
```

- [ ] **Step 3: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/org-chart/page.tsx
git commit -m "polish(org-chart): upgrade header to premium gradient style"
```

---

### Task 14: Polish Approval Token Page

**Files:**
- Modify: `frontend/src/app/approval/[token]/page.tsx`

**What changes:**
- Add `PremiumShell` wrapper
- Add branded header with Pikar logo/gradient
- Upgrade approve/reject buttons to premium styling
- Add `motion` entrance animation

- [ ] **Step 1: Add PremiumShell, motion, gradient branded header**

- [ ] **Step 2: Upgrade action buttons to premium rounded-2xl style with teal/red gradients**

- [ ] **Step 3: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/approval/\[token\]/page.tsx
git commit -m "polish(approval): upgrade approval page to branded premium design"
```

---

### Task 15: Polish Public Pages

**Files:**
- Modify: `frontend/src/app/p/[id]/page.tsx`

**What changes:**
- Add minimal branding (Pikar logo in header)
- Replace raw `dangerouslySetInnerHTML` with prose-styled wrapper
- Add `motion` entrance animation

- [ ] **Step 1: Add branded header with logo**

- [ ] **Step 2: Wrap HTML content in prose container with premium card styling**

```typescript
<div className="mx-auto max-w-4xl p-6">
  <div className="rounded-[28px] border border-slate-100/80 bg-white p-8 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
    <div className="prose prose-slate prose-lg max-w-none" dangerouslySetInnerHTML={{ __html: content }} />
  </div>
</div>
```

- [ ] **Step 3: Verify build and commit**

```bash
cd frontend && npx next build
git add frontend/src/app/p/\[id\]/page.tsx
git commit -m "polish(public): add branding and premium styling to public pages"
```

---

## Final Verification

### Task 16: Full Build + Visual Audit

- [ ] **Step 1: Run full build**

```bash
cd frontend && npx next build
```

- [ ] **Step 2: Run lint**

```bash
cd frontend && npx next lint
```

- [ ] **Step 3: Run tests**

```bash
cd frontend && npx vitest run
```

- [ ] **Step 4: Final commit if any remaining fixes**

Stage only the specific files that were fixed:
```bash
git add frontend/src/app/dashboard/workflows/ frontend/src/app/dashboard/initiatives/ frontend/src/app/dashboard/journeys/ frontend/src/components/braindump/ frontend/src/app/settings/ frontend/src/app/departments/ frontend/src/app/org-chart/ frontend/src/app/approval/ frontend/src/app/p/
git commit -m "polish: final build fixes after premium design upgrade"
```
