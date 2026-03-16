# Mobile Responsiveness — Full App

**Date:** 2026-03-16
**Status:** Approved
**Scope:** All pages and components across 375px → 1366px breakpoints

---

## 1. Overview

Make the entire Pikar-AI app mobile responsive — not just the landing page (already done) but all authenticated pages, auth flows, dashboard content, chat interface, settings, approvals, and data deletion pages. Includes a swipe-to-open sidebar gesture and 44px minimum tap targets.

### Breakpoint Strategy

| Token | Width | Role |
|-------|-------|------|
| `sm:` | 640px | Large phones / small tablets |
| `md:` | 768px | Tablets — sidebar visibility threshold |
| `lg:` | 1024px | Small laptops |
| `xl:` | 1280px | Desktop |

### Grid Progression (dashboard cards)

`1 col (base) → 2 col (sm:) → 2 col (md:) → 4 col (lg:)`

Stays at 2 columns through the tablet range for card readability.

### Viewport Meta Tag

Add `viewport-fit=cover` to the root layout's meta viewport tag. This is **required** for `env(safe-area-inset-*)` to return non-zero values on iOS devices with notches/home indicators:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

**Location:** `frontend/src/app/layout.tsx`

---

## 2. Auth Pages

### Login & Signup (`LoginPage.tsx`, `SignupPage.tsx`)

**Problem:** Two-column split layout only activates at `lg:` (1024px). Below that, layout is broken.

**Fix:**
- Left decorative panel (feature cards, branding): add `hidden md:flex` — hidden on phones and small tablets, visible from 768px. Preserve all existing layout classes (`flex-col`, `justify-between`, `h-full`, `relative`, `z-10`, `bg-white/50`, `backdrop-blur-sm`).
- Form section: full-width centered on screens below `md:`
- Form container: keep `max-w-sm` with padding `px-4 sm:px-6`
- Social auth buttons: stack vertically on phones, horizontal on `sm:` and up
- Footer: change from `hidden lg:block` to `hidden md:block`
- Login form must be scrollable in landscape orientation

**Classes to change (LoginPage.tsx):**
```
// Left panel — ADD hidden md:flex, change lg: prefixes to md:
// Keep all existing classes, only change responsive prefixes
- BEFORE: <div className="w-full lg:w-1/2 p-4 lg:p-8 xl:p-10 flex flex-col justify-between h-full relative z-10 bg-white/50 backdrop-blur-sm">
- AFTER:  <div className="hidden md:flex md:w-1/2 p-4 md:p-8 xl:p-10 flex-col justify-between h-full relative z-10 bg-white/50 backdrop-blur-sm">

// Right panel (form) — change lg: to md:
- BEFORE: <div className="w-full lg:w-1/2 flex items-center justify-center p-4 lg:p-8 ...">
- AFTER:  <div className="w-full md:w-1/2 flex items-center justify-center p-4 md:p-8 ...">

// Footer
- BEFORE: hidden lg:block
- AFTER:  hidden md:block
```

**SignupPage.tsx:** Identical changes — same two-column structure with matching class names.

### Reset Password (`ResetPasswordPage.tsx`)

- Add responsive padding: `px-4 sm:px-6` on the outer container
- Form fields: enforce `h-11` (44px) minimum height

### Forgot Password

- No changes needed — already responsive.

---

## 3. Dashboard Layout & Navigation

### Primary Layout: `PremiumShell.tsx`

The main authenticated layout is `PremiumShell.tsx` (not `DashboardLayout.tsx`). It already has:
- Mobile slide-over sidebar (lines 182-233)
- Hamburger menu button (lines 268-277)
- Mobile detection via `window.matchMedia('(max-width: 768px)')`
- `h-[100dvh]` for proper mobile viewport handling

`DashboardLayout.tsx` is a simpler legacy shell. Both need the swipe gesture for backward compatibility.

### Sidebar Swipe Gesture

**New behavior (below `md:` only):**
- Swipe left-to-right from left edge (within 20px) to open sidebar
- Swipe right-to-left on open sidebar to close
- Minimum swipe distance: 75px to trigger
- Sidebar slides via `transform: translateX()` with 300ms ease-out transition
- Semi-transparent backdrop overlay; tapping backdrop also closes
- `touch-action: pan-y` on main content to avoid vertical scroll conflicts
- When sidebar is open and its content is scrollable, vertical touch scrolling within the sidebar must still work

**Implementation:** Create `frontend/src/hooks/useSwipeGesture.ts` custom hook. Integrate into both `PremiumShell.tsx` (primary) and `DashboardLayout.tsx` (legacy).

**Desktop (`md:` and up):** No changes — current sidebar behavior preserved.

### Header (`Header.tsx`)

- User profile: compact avatar-only below `sm:`, full name+avatar on `sm:` and up
- Change `hidden sm:flex` to show avatar icon on mobile
- Hamburger menu button: remains `md:hidden`

### PremiumShell Mobile Sidebar Width

- Mobile overlay sidebar: `w-64 sm:w-72` (from fixed `w-72`)
- Desktop sidebar uses framer-motion inline styles (COLLAPSED_WIDTH=60px, EXPANDED_WIDTH=260px) — no changes needed

---

## 4. Dashboard Content Grids

### CommandCenter (`CommandCenter.tsx`)

All grid changes apply to both the loading skeleton grids AND the actual content grids. Find by class pattern, not line number.

| Grid Pattern | Before | After |
|------|--------|-------|
| 4-col grids (loading skeletons, KPI cards) | `grid gap-4 md:grid-cols-4` | `grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-4` |
| 2→4-col grids (launchpad, activity) | `grid gap-4 md:grid-cols-2 xl:grid-cols-4` | `grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-4` |
| Hero flex layout | `flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between` | `flex flex-col gap-6 sm:gap-8 md:flex-row md:items-end md:justify-between` |
| Founder board grids (inside `renderFounderBoard`) | `grid gap-6 lg:grid-cols-[...]` | `grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-[...]` |

### PersonaDashboardLayout (`PersonaDashboardLayout.tsx`)

- This component delegates content rendering to `<CommandCenter>` — no content grids to change here
- Any wrapper grids: add `md:grid-cols-2` intermediate if present

### Settings Page

- DeleteAccountModal: `w-full sm:max-w-md` (full-width on phones, constrained on larger)
- "DELETE" confirmation input: `h-11` (44px) minimum
- Danger Zone section: responsive padding

---

## 5. Chat Interface — Full-Screen Mobile

### Chat Component Breakdown

| File | Mobile Changes |
|------|---------------|
| `ChatInterface.tsx` | Wrapper: `fixed inset-0 z-50` below `md:`, back button, `h-[100dvh]` |
| `MessageItem.tsx` | Max-width constraint on bubbles, responsive text size, responsive padding |
| `AudioRecorder.tsx` | 44px tap targets on record/stop buttons |
| `FileDropZone.tsx` | Full-width drop area on mobile, responsive icon/text sizing |
| `SessionList.tsx` | 44px min-height per session item, swipe-to-delete if applicable |
| `ThoughtProcess.tsx` | Collapsible on mobile, responsive typography |

### Below `md:` (768px)

- Chat fills viewport: `fixed inset-0 z-50` with `h-[100dvh]` (matches PremiumShell pattern)
- Top bar: back button (44px, left) + agent name/avatar (center)
- Message list: `flex-1 overflow-y-auto` fills remaining height
- Input bar: `sticky bottom-0` with `pb-[env(safe-area-inset-bottom)]` for iPhone X+ home indicator
- Send button and attachment buttons: 44px x 44px minimum

### Virtual Keyboard Handling

Mobile keyboards push content up and can obscure the fixed input bar. Strategy:

- Use `h-[100dvh]` instead of `h-screen` — dynamic viewport height automatically adjusts when keyboard opens on modern browsers
- Add `interactive-widget=resizes-content` to the viewport meta tag for Chrome Android
- Listen to `visualViewport.resize` event as fallback for older browsers — adjust input bar position when viewport height shrinks (keyboard open)
- Input bar uses `position: sticky; bottom: 0` within a flex container rather than `position: fixed` — this naturally adjusts with the visual viewport

### Landscape Mode

- Login/signup form container: add `overflow-y-auto max-h-[100dvh]` so the form scrolls in landscape
- Chat interface: input bar height reduces to `h-10` (40px) in landscape to preserve message viewing area — use `@media (orientation: landscape) and (max-height: 500px)` via Tailwind arbitrary variant or CSS
- Sidebar: ensure `max-h-[100dvh] overflow-y-auto` in landscape

### `md:` and up

- No changes — current desktop layout preserved.

---

## 6. Touch Optimization (Global, below `md:`)

### 44px Minimum Tap Targets

| Element | Current | Fix |
|---------|---------|-----|
| Buttons | varies | `min-h-[44px] min-w-[44px]` |
| Sidebar nav links | `py-2` | `py-3` |
| Form inputs | ~40px | `h-11` (44px) |
| Icon buttons | `w-10 h-10` | `w-11 h-11` |
| List items (sessions, approvals) | varies | `min-h-[44px]` |

### Spacing

- Minimum 8px gap (`gap-2`) between adjacent interactive elements
- Prevents mis-taps on mobile

### Approval Components

- Approve/reject buttons: `flex-col sm:flex-row` (stack on mobile)
- Cards: responsive padding, text truncation for long names

### Data Deletion Pages

- List margins in "How to Request Deletion" section: `ml-6 sm:ml-8 md:ml-11` (from fixed `ml-11`)
- Status page cards: `p-3 sm:p-4`

### Scrolling

- Wrap any horizontal-overflow content in `overflow-x-auto` containers
- Note: `-webkit-overflow-scrolling: touch` is deprecated and default since iOS 13 — not needed

---

## 7. Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/app/layout.tsx` | Add `viewport-fit=cover` and `interactive-widget=resizes-content` to meta viewport |
| `frontend/src/app/auth/login/LoginPage.tsx` | Hide left panel below md, responsive form, landscape scroll |
| `frontend/src/app/auth/signup/SignupPage.tsx` | Identical to LoginPage changes |
| `frontend/src/app/auth/reset-password/ResetPasswordPage.tsx` | Responsive padding, 44px inputs |
| `frontend/src/components/layout/PremiumShell.tsx` | Swipe gesture (primary), responsive mobile sidebar width |
| `frontend/src/components/layout/DashboardLayout.tsx` | Swipe gesture (legacy compat) |
| `frontend/src/components/layout/Sidebar.tsx` | Slide transition, touch targets on nav links |
| `frontend/src/components/layout/Header.tsx` | Mobile avatar-only, responsive profile |
| `frontend/src/components/dashboard/CommandCenter.tsx` | Grid breakpoints (all grids including renderFounderBoard) |
| `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` | Wrapper grid breakpoints if present |
| `frontend/src/components/chat/ChatInterface.tsx` | Full-screen mobile takeover, keyboard handling |
| `frontend/src/components/chat/MessageItem.tsx` | Responsive bubble width, text size, padding |
| `frontend/src/components/chat/AudioRecorder.tsx` | 44px tap targets |
| `frontend/src/components/chat/FileDropZone.tsx` | Full-width mobile, responsive sizing |
| `frontend/src/components/chat/SessionList.tsx` | 44px min-height items |
| `frontend/src/components/chat/ThoughtProcess.tsx` | Collapsible mobile, responsive typography |
| `frontend/src/app/settings/page.tsx` | Modal + danger zone responsive |
| `frontend/src/app/data-deletion/page.tsx` | Responsive list margins |
| `frontend/src/app/data-deletion/status/page.tsx` | Responsive card padding |
| `frontend/src/app/globals.css` | Landscape media queries, safe area utilities |
| New: `frontend/src/hooks/useSwipeGesture.ts` | Reusable swipe gesture hook |

---

## 8. Out of Scope

- Landing page (already responsive)
- Forgot password page (already responsive)
- Desktop layout changes (all changes are additive responsive classes)
- New features or functionality — this is purely layout/responsiveness
- Onboarding flow (if exists, separate effort)
