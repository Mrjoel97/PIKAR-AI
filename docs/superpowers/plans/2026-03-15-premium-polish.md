# Premium Polish Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade all dashboard interfaces from "Standard" design to match CommandCenter's premium design language — consistent shadows, border-radius, typography, animations, and backgrounds.

**Architecture:** Upgrade shared components (MetricCard, StatusBadge) first for maximum cascade effect, then polish each dashboard page individually. All pages must use PremiumShell layout wrapper with bg-slate-50 backgrounds.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4, framer-motion 12, lucide-react

---

## Design Token Reference (from CommandCenter.tsx)

| Token | Standard (Current) | Premium (Target) |
|-------|-------------------|------------------|
| Card radius | `rounded-2xl` | `rounded-[28px]` |
| Card shadow | `shadow-sm` | `shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)]` |
| Section shadow | `shadow-sm` | `shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]` |
| Page background | `bg-white` | `bg-slate-50` |
| Card background | `bg-white` | `bg-white/95` or `bg-white` |
| Eyebrow text | `text-xs tracking-wider` | `text-[11px] tracking-[0.28em]` |
| Section title | `text-sm tracking-wider` | `text-sm tracking-[0.28em]` |
| Entry animation | none | `initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}` |
| Icon bg | flat `bg-[color]-50` | `bg-gradient-to-br from-[color]-400 to-[color]-500` with white icon |
| Border | `border border-slate-100` | `border border-slate-100/80` |
| Button radius | `rounded-lg` | `rounded-2xl` |

---

## Task 1: Upgrade MetricCard.tsx (Shared Component)

**Files:**
- Modify: `frontend/src/components/ui/MetricCard.tsx`

- [ ] **Step 1: Upgrade MetricCard to premium design**

Replace entire component with premium version:
- `rounded-[28px]` border radius
- `shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)]` shadow
- `text-[11px] tracking-[0.28em]` eyebrow label
- Gradient icon background (accept `gradient` prop as string)
- `border-slate-100/80`
- framer-motion fade-in animation

- [ ] **Step 2: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 3: Commit**

---

## Task 2: Upgrade StatusBadge.tsx (Minor Polish)

**Files:**
- Modify: `frontend/src/components/ui/StatusBadge.tsx`

- [ ] **Step 1: Add subtle backdrop-blur and refined pill shape**

- Add `backdrop-blur-sm` to pill variant
- Add `shadow-sm` to default variant
- Keep all color mappings unchanged

- [ ] **Step 2: Commit**

---

## Task 3: Upgrade Finance Dashboard

**Files:**
- Modify: `frontend/src/app/dashboard/finance/page.tsx`

- [ ] **Step 1: Apply premium tokens**

- Wrap in PremiumShell
- `bg-white` → `bg-slate-50` page background (PremiumShell handles this)
- Remove `min-h-screen bg-white` from wrapper divs
- `rounded-2xl` → `rounded-[28px]` on all section cards
- `shadow-sm` → `shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]` on section cards
- `tracking-wider` → `tracking-[0.28em]` on eyebrow labels
- Add `text-[11px]` to eyebrow labels (replace `text-sm`)
- Add framer-motion `<motion.div>` wrappers with staggered entry
- Revenue chart bars: `rounded-t-md` → `rounded-t-lg`, add gradient
- Loading skeleton: `rounded-2xl` → `rounded-[28px]`
- Header button: `rounded-lg` → `rounded-2xl`

- [ ] **Step 2: Verify build compiles**
- [ ] **Step 3: Commit**

---

## Task 4: Upgrade Sales Pipeline Dashboard

**Files:**
- Modify: `frontend/src/app/dashboard/sales/page.tsx`

- [ ] **Step 1: Apply premium tokens**

Same token upgrades as Finance, plus:
- Kanban column cards: `rounded-[28px]`, premium shadows
- Contact cards: `rounded-xl` → `rounded-2xl`
- Tab buttons: refined pill shape with `rounded-2xl`
- Channel monitor cards: premium card treatment

- [ ] **Step 2: Verify build compiles**
- [ ] **Step 3: Commit**

---

## Task 5: Upgrade Compliance Dashboard

**Files:**
- Modify: `frontend/src/app/dashboard/compliance/page.tsx`

- [ ] **Step 1: Apply premium tokens**

Same token upgrades as Finance, plus:
- Risk severity bar: smoother gradient segments
- Timeline dots: add glow effect
- Risk cards: premium card treatment

- [ ] **Step 2: Verify build compiles**
- [ ] **Step 3: Commit**

---

## Task 6: Upgrade Content Calendar Dashboard

**Files:**
- Modify: `frontend/src/app/dashboard/content/page.tsx`

- [ ] **Step 1: Apply premium tokens**

Same token upgrades as Finance, plus:
- Calendar cells: refined borders, hover states
- Content chips: subtle shadows, gradient accents
- List view cards: premium treatment

- [ ] **Step 2: Verify build compiles**
- [ ] **Step 3: Commit**

---

## Task 7: Upgrade Billing Page

**Files:**
- Modify: `frontend/src/app/dashboard/billing/page.tsx`

- [ ] **Step 1: Apply premium tokens**

- Plan card: `rounded-[28px]`, premium shadow
- Usage stat cards: MetricCard (already upgraded)
- Comparison table: refined borders, premium hover states
- CTA buttons: `rounded-2xl`, gradient backgrounds

- [ ] **Step 2: Verify build compiles**
- [ ] **Step 3: Commit**

---

## Task 8: Wrap Remaining Pages in PremiumShell

**Files to check/modify:**
- `frontend/src/app/dashboard/finance/page.tsx` — needs PremiumShell wrap
- `frontend/src/app/dashboard/sales/page.tsx` — needs PremiumShell wrap
- `frontend/src/app/dashboard/compliance/page.tsx` — needs PremiumShell wrap
- `frontend/src/app/dashboard/content/page.tsx` — needs PremiumShell wrap
- `frontend/src/app/dashboard/billing/page.tsx` — needs PremiumShell wrap

These 5 new dashboards currently render standalone (no sidebar). Wrapping in PremiumShell gives them the sidebar navigation.

- [ ] **Step 1: Add PremiumShell wrapper to each page**
- [ ] **Step 2: Verify sidebar appears on all pages**
- [ ] **Step 3: Commit**

---

## Verification

1. `cd frontend && npm run build` — all pages compile
2. Visual check: each dashboard has bg-slate-50, rounded-[28px] cards, premium shadows
3. Sidebar visible on all dashboard pages
4. Framer-motion animations play on page load
5. MetricCard gradient icons render across all dashboards
