# Mobile Responsiveness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the entire Pikar-AI app fully mobile responsive from 375px to 1366px, including auth pages, dashboard, chat, settings, and data deletion pages.

**Architecture:** Additive responsive Tailwind classes at sm:/md:/lg: breakpoints. New `useSwipeGesture` hook for sidebar gesture. Full-screen chat takeover on mobile. No desktop layout changes.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4, TypeScript, framer-motion

**Spec:** `docs/superpowers/specs/2026-03-16-mobile-responsiveness-design.md`

---

## Chunk 1: Foundation & Auth Pages

### Task 1: Viewport Meta Tag & Global CSS

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add viewport-fit=cover to root layout**

In `frontend/src/app/layout.tsx`, add a viewport export after the metadata export. Next.js App Router uses the `viewport` export for the viewport meta tag:

```tsx
export const viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover' as const,
  interactiveWidget: 'resizes-content' as const,
};
```

Add this after the `metadata` export (around line 50). This enables `env(safe-area-inset-*)` on iOS and proper keyboard behavior on Android.

- [ ] **Step 2: Add landscape and safe-area utilities to globals.css**

Append to `frontend/src/app/globals.css` after the existing styles:

```css
/* Mobile Safe Area Utilities */
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

/* Landscape compact mode — targets phones in landscape */
@media (orientation: landscape) and (max-height: 500px) {
  .landscape-compact-input {
    height: 2.5rem; /* 40px instead of 44px */
  }
}
```

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build --no-lint 2>&1 | tail -5`
Expected: Build succeeds (or only lint warnings)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css
git commit -m "feat: add viewport-fit=cover and mobile CSS utilities"
```

---

### Task 2: LoginPage Mobile Responsive

**Files:**
- Modify: `frontend/src/app/auth/login/LoginPage.tsx`

- [ ] **Step 1: Hide left decorative panel below md breakpoint**

In `frontend/src/app/auth/login/LoginPage.tsx`, change the outer `<main>` tag (line 99):

```
// BEFORE:
<main className="relative z-10 w-full h-screen flex flex-col lg:flex-row">

// AFTER:
<main className="relative z-10 w-full h-[100dvh] flex flex-col md:flex-row overflow-y-auto">
```

- [ ] **Step 2: Hide left section on mobile, show on md+**

Change the left `<section>` tag (line 101):

```
// BEFORE:
<section className="w-full lg:w-1/2 p-4 lg:p-8 xl:p-10 flex flex-col justify-between h-full relative z-10 bg-white/50 backdrop-blur-sm">

// AFTER:
<section className="hidden md:flex md:w-1/2 p-4 md:p-8 xl:p-10 flex-col justify-between h-full relative z-10 bg-white/50 backdrop-blur-sm">
```

- [ ] **Step 3: Make right (form) section responsive**

Change the right `<section>` tag (line 167):

```
// BEFORE:
<section className="w-full lg:w-1/2 flex items-center justify-center p-4 lg:p-8 relative h-full bg-gradient-to-br from-teal-700 via-teal-800 to-slate-900">

// AFTER:
<section className="w-full md:w-1/2 flex items-center justify-center p-4 md:p-8 relative h-full min-h-[100dvh] md:min-h-0 bg-gradient-to-br from-teal-700 via-teal-800 to-slate-900">
```

- [ ] **Step 4: Fix footer visibility**

Change the desktop footer (line 161):

```
// BEFORE:
<div className="text-xs text-slate-400 hidden lg:block">

// AFTER:
<div className="text-xs text-slate-400 hidden md:block">
```

Change the mobile footer (line 292):

```
// BEFORE:
<div className="lg:hidden absolute bottom-4 left-0 right-0 text-center text-teal-200/50 text-xs">

// AFTER:
<div className="md:hidden absolute bottom-4 left-0 right-0 text-center text-teal-200/50 text-xs">
```

- [ ] **Step 5: Increase form input touch targets**

Change both input fields' `py-2.5` to ensure 44px minimum. The inputs (lines 207, 228) already have `py-2.5` which is ~40px with text. Add `min-h-[44px]`:

On the email input (line 207):
```
// BEFORE:
className="w-full bg-white/10 border border-white/20 rounded-lg py-2.5 pl-10 pr-3 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm"

// AFTER:
className="w-full bg-white/10 border border-white/20 rounded-lg py-2.5 pl-10 pr-3 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
```

Apply the same `min-h-[44px]` to the password input (line 228) and the submit button (line 246).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/auth/login/LoginPage.tsx
git commit -m "feat: make login page mobile responsive — hide left panel below md"
```

---

### Task 3: SignupPage Mobile Responsive

**Files:**
- Modify: `frontend/src/app/auth/signup/SignupPage.tsx`

- [ ] **Step 1: Apply identical changes as LoginPage**

The SignupPage has the same two-column structure. Apply these changes:

Line 100 outer div: change `h-screen` to `h-[100dvh]`

Line 104 `<main>`: change `lg:flex-row` to `md:flex-row`, add `overflow-y-auto`

Line 106 left `<section>`: change from `w-full lg:w-1/2 p-4 lg:p-8 xl:p-10 flex flex-col` to `hidden md:flex md:w-1/2 p-4 md:p-8 xl:p-10 flex-col`

Line 166 footer: change `hidden lg:block` to `hidden md:block`

Line 172 right `<section>`: change `w-full lg:w-1/2 flex items-center justify-center p-4 lg:p-6` to `w-full md:w-1/2 flex items-center justify-center p-4 md:p-6 min-h-[100dvh] md:min-h-0`

Line 332 mobile footer: change `lg:hidden` to `md:hidden`

Add `min-h-[44px]` to all four input fields (lines 210, 230, 249, 274) and the submit button (line 286).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/auth/signup/SignupPage.tsx
git commit -m "feat: make signup page mobile responsive — hide left panel below md"
```

---

### Task 4: ResetPasswordPage Touch Targets

**Files:**
- Modify: `frontend/src/app/auth/reset-password/ResetPasswordPage.tsx`

- [ ] **Step 1: Add responsive padding to outer container**

Line 54 `<main>`:
```
// BEFORE:
<main className="relative z-10 w-full max-w-[480px]">

// AFTER:
<main className="relative z-10 w-full max-w-[480px] px-4 sm:px-0">
```

The inputs already have `h-14` (56px) which exceeds 44px. No input changes needed.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/auth/reset-password/ResetPasswordPage.tsx
git commit -m "feat: add responsive padding to reset password page"
```

---

## Chunk 2: Swipe Gesture Hook & Sidebar

### Task 5: Create useSwipeGesture Hook

**Files:**
- Create: `frontend/src/hooks/useSwipeGesture.ts`

- [ ] **Step 1: Create the hook file**

```typescript
import { useEffect, useRef, useCallback } from 'react';

interface SwipeGestureOptions {
  /** Called when swipe-right from left edge is detected (open) */
  onSwipeOpen: () => void;
  /** Called when swipe-left is detected (close) */
  onSwipeClose: () => void;
  /** Whether the sidebar is currently open */
  isOpen: boolean;
  /** Whether gesture detection is enabled (disable on desktop) */
  enabled: boolean;
  /** Max X position from left edge to start swipe-open (default: 20px) */
  edgeThreshold?: number;
  /** Min horizontal distance to trigger (default: 75px) */
  minSwipeDistance?: number;
}

export function useSwipeGesture({
  onSwipeOpen,
  onSwipeClose,
  isOpen,
  enabled,
  edgeThreshold = 20,
  minSwipeDistance = 75,
}: SwipeGestureOptions) {
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const touchCurrent = useRef<{ x: number } | null>(null);

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      if (!enabled) return;
      const touch = e.touches[0];
      touchStart.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
      touchCurrent.current = { x: touch.clientX };
    },
    [enabled]
  );

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!enabled || !touchStart.current) return;
      touchCurrent.current = { x: e.touches[0].clientX };
    },
    [enabled]
  );

  const handleTouchEnd = useCallback(() => {
    if (!enabled || !touchStart.current || !touchCurrent.current) {
      touchStart.current = null;
      touchCurrent.current = null;
      return;
    }

    const deltaX = touchCurrent.current.x - touchStart.current.x;
    const startX = touchStart.current.x;

    if (!isOpen && startX <= edgeThreshold && deltaX >= minSwipeDistance) {
      // Swipe right from left edge → open
      onSwipeOpen();
    } else if (isOpen && deltaX <= -minSwipeDistance) {
      // Swipe left while open → close
      onSwipeClose();
    }

    touchStart.current = null;
    touchCurrent.current = null;
  }, [enabled, isOpen, edgeThreshold, minSwipeDistance, onSwipeOpen, onSwipeClose]);

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [enabled, handleTouchStart, handleTouchMove, handleTouchEnd]);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useSwipeGesture.ts
git commit -m "feat: add useSwipeGesture hook for mobile sidebar navigation"
```

---

### Task 6: Integrate Swipe Gesture into PremiumShell

**Files:**
- Modify: `frontend/src/components/layout/PremiumShell.tsx`

- [ ] **Step 1: Import the hook**

Add at top of file (after existing imports):

```typescript
import { useSwipeGesture } from '@/hooks/useSwipeGesture';
```

- [ ] **Step 2: Add the hook call inside PremiumShell component**

After the existing `useEffect` blocks (around line 97, after `handleSignOut`), add:

```typescript
useSwipeGesture({
    onSwipeOpen: () => setIsMobileNavOpen(true),
    onSwipeClose: () => setIsMobileNavOpen(false),
    isOpen: isMobileNavOpen,
    enabled: isMobile,
});
```

- [ ] **Step 3: Make mobile sidebar width responsive**

Line 189, change:
```
// BEFORE:
className={`absolute left-0 top-0 bottom-0 w-72 bg-teal-900 border-r border-teal-800/60 shadow-[4px_0_30px_-12px_rgba(0,0,0,0.3)] transform transition-transform flex flex-col ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}

// AFTER:
className={`absolute left-0 top-0 bottom-0 w-64 sm:w-72 bg-teal-900 border-r border-teal-800/60 shadow-[4px_0_30px_-12px_rgba(0,0,0,0.3)] transform transition-transform duration-300 ease-out flex flex-col max-h-[100dvh] overflow-y-auto ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}
```

- [ ] **Step 4: Add touch-action to main content area**

Line 261, on the `<main>` element, add `touch-action-pan-y` style:
```
// BEFORE:
className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar bg-slate-50 h-full"

// AFTER:
className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar bg-slate-50 h-full"
style={{
    marginLeft: shouldShowChatPanel ? `${chatWidth}%` : '0',
    width: shouldShowChatPanel ? `${100 - chatWidth}%` : '100%',
    touchAction: 'pan-y',
}}
```

Note: merge with existing `style` prop — combine both objects.

- [ ] **Step 5: Increase mobile nav link touch targets**

In the NavItem component (line 291), change `py-2.5` to `py-3`:
```
// BEFORE:
w-full flex items-center ${collapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-xl

// AFTER:
w-full flex items-center ${collapsed ? 'justify-center' : 'px-3'} py-3 rounded-xl
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/PremiumShell.tsx
git commit -m "feat: add swipe gesture sidebar navigation and responsive width"
```

---

### Task 7: Integrate Swipe Gesture into DashboardLayout (Legacy)

**Files:**
- Modify: `frontend/src/components/layout/DashboardLayout.tsx`

- [ ] **Step 1: Import hook and add mobile detection**

```typescript
import { useSwipeGesture } from '@/hooks/useSwipeGesture';
import { useState, useEffect } from 'react';
```

Update the existing `useState` import to include `useEffect`.

- [ ] **Step 2: Add mobile detection and swipe gesture**

Inside the `DashboardLayout` function, after the existing `isMobileMenuOpen` state, add:

```typescript
const [isMobile, setIsMobile] = useState(false);

useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)');
    const update = () => setIsMobile(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
}, []);

useSwipeGesture({
    onSwipeOpen: () => setIsMobileMenuOpen(true),
    onSwipeClose: () => setIsMobileMenuOpen(false),
    isOpen: isMobileMenuOpen,
    enabled: isMobile,
});
```

- [ ] **Step 3: Add transition to mobile sidebar overlay**

Line 25, change:
```
// BEFORE:
<div className="absolute left-0 top-0 bottom-0 w-64 bg-white">

// AFTER:
<div className="absolute left-0 top-0 bottom-0 w-64 bg-white transform transition-transform duration-300 ease-out max-h-[100dvh] overflow-y-auto">
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/DashboardLayout.tsx
git commit -m "feat: add swipe gesture to legacy DashboardLayout"
```

---

## Chunk 3: Dashboard Grids & Header

### Task 8: CommandCenter Grid Breakpoints

**Files:**
- Modify: `frontend/src/components/dashboard/CommandCenter.tsx`

- [ ] **Step 1: Fix the 4-col loading skeleton grid (line 308)**

```
// BEFORE:
<div className="grid gap-4 md:grid-cols-4">

// AFTER:
<div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-4">
```

- [ ] **Step 2: Fix the 2→4 col grids (lines 341, 402, 414)**

For each of these three grids:
```
// BEFORE:
<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">

// AFTER:
<div className="grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-4">
```

- [ ] **Step 3: Fix the hero flex layout (line 373)**

```
// BEFORE:
<div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">

// AFTER:
<div className="relative flex flex-col gap-6 sm:gap-8 md:flex-row md:items-end md:justify-between">
```

- [ ] **Step 4: Fix the founder board grids (lines 177, 212, 241, 275, 311)**

For each `grid gap-6 lg:grid-cols-[...]` instance:
```
// BEFORE:
<div className="grid gap-6 lg:grid-cols-[1.25fr_0.95fr]">

// AFTER:
<div className="grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-[1.25fr_0.95fr]">
```

Apply the same pattern to lines 212, 241, 275 (different fractional ratios — keep those, just add `gap-4 sm:gap-6 md:grid-cols-2`).

Line 311:
```
// BEFORE:
<div className="grid gap-6 lg:grid-cols-2">

// AFTER:
<div className="grid gap-4 sm:gap-6 md:grid-cols-2">
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/CommandCenter.tsx
git commit -m "feat: add responsive grid breakpoints to CommandCenter"
```

---

### Task 9: Header Mobile Profile

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`

- [ ] **Step 1: Avatar is already visible on mobile (line 45)**

The avatar `<div>` at line 45 has no `hidden` class — it's always visible. Good.

The text info at line 48 uses `hidden sm:flex` — hidden on phones, shown on sm+. This is acceptable. No changes needed.

- [ ] **Step 2: Increase hamburger menu tap target**

Line 26:
```
// BEFORE:
className="md:hidden p-2 hover:bg-gray-100 rounded-lg"

// AFTER:
className="md:hidden p-2.5 hover:bg-gray-100 rounded-lg min-h-[44px] min-w-[44px] flex items-center justify-center"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/Header.tsx
git commit -m "feat: increase header hamburger tap target to 44px"
```

---

## Chunk 4: Chat Mobile Takeover

### Task 10: ChatInterface Full-Screen Mobile

**Files:**
- Modify: `frontend/src/components/chat/ChatInterface.tsx`

- [ ] **Step 1: Add mobile detection state**

Inside the `ChatInterface` function, after existing state declarations, add:

```typescript
const [isMobile, setIsMobile] = useState(false);

useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)');
    const update = () => setIsMobile(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
}, []);
```

- [ ] **Step 2: Make the outer container full-screen on mobile**

Find the outer wrapper div (line 752):
```
// BEFORE:
<div className={className || "relative h-[600px] bg-white dark:bg-slate-900 rounded-2xl shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] border border-slate-100/80 dark:border-slate-800 overflow-hidden"}>

// AFTER:
<div className={className || `${isMobile ? 'fixed inset-0 z-50 h-[100dvh]' : 'relative h-[600px] rounded-2xl shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] border border-slate-100/80 dark:border-slate-800'} bg-white dark:bg-slate-900 overflow-hidden`}>
```

- [ ] **Step 3: Add safe area bottom padding to input area**

Find the input container (line 932):
```
// BEFORE:
<div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-100/80 dark:border-slate-800">

// AFTER:
<div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-100/80 dark:border-slate-800 safe-area-bottom">
```

- [ ] **Step 4: Increase send button and action button tap targets**

Find the send button and ensure it has `min-h-[44px] min-w-[44px]`. Find the mic button, attach button, and any icon-only buttons in the input area — add the same sizing.

Search for the send button (look for `Send` icon usage) and mic/attach buttons and add:
```
min-h-[44px] min-w-[44px]
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chat/ChatInterface.tsx
git commit -m "feat: full-screen mobile chat takeover with safe area support"
```

---

### Task 11: MessageItem Responsive

**Files:**
- Modify: `frontend/src/components/chat/MessageItem.tsx`

- [ ] **Step 1: Add responsive padding to message bubbles**

Find the message bubble wrapper classes and ensure responsive text sizing. Look for the main message container classes and add:
- `text-sm sm:text-base` for message text
- `p-3 sm:p-4` for message padding
- `max-w-[95%] sm:max-w-[85%] md:max-w-[75%]` for bubble width on mobile

These changes should be applied to the message container elements within the component — read the full file to find the exact class strings and apply responsive variants.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/MessageItem.tsx
git commit -m "feat: responsive message bubbles for mobile chat"
```

---

## Chunk 5: Settings, Data Deletion & Final Polish

### Task 12: Settings Page — DeleteAccountModal Responsive

**Files:**
- Modify: `frontend/src/app/settings/page.tsx`

- [ ] **Step 1: Make DeleteAccountModal full-width on mobile**

Find the modal container (around line 103, the `DeleteAccountModal` component). Look for the modal's inner card/panel div and change its width class:

```
// Target the modal panel — look for max-w-md or similar
// BEFORE: (something like)
className="... max-w-md ..."

// AFTER:
className="... w-full sm:max-w-md mx-4 sm:mx-auto ..."
```

- [ ] **Step 2: Ensure DELETE input has 44px height**

Find the text input where users type "DELETE" and add `h-11`:

```
// Add to the input's className:
h-11 min-h-[44px]
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/settings/page.tsx
git commit -m "feat: responsive delete account modal for mobile"
```

---

### Task 13: Data Deletion Pages Responsive

**Files:**
- Modify: `frontend/src/app/data-deletion/page.tsx`
- Modify: `frontend/src/app/data-deletion/status/page.tsx`

- [ ] **Step 1: Fix list margins on data-deletion page**

In `frontend/src/app/data-deletion/page.tsx`, find the ordered list with `ml-11` (around line 110):

```
// BEFORE:
ml-11

// AFTER:
ml-6 sm:ml-8 md:ml-11
```

Apply to any other `ml-11` occurrences in the file.

- [ ] **Step 2: Fix status page card padding**

In `frontend/src/app/data-deletion/status/page.tsx`, find card padding classes and make responsive:

```
// Look for p-4 or p-6 on card containers
// BEFORE:
p-4

// AFTER:
p-3 sm:p-4
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/data-deletion/page.tsx frontend/src/app/data-deletion/status/page.tsx
git commit -m "feat: responsive margins and padding on data deletion pages"
```

---

### Task 14: Visual Testing

**Files:** None (manual verification)

- [ ] **Step 1: Start dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Test at key breakpoints**

Open browser DevTools → responsive mode. Test each page at:
- 375px (iPhone SE)
- 390px (iPhone 14)
- 768px (iPad)
- 1024px (iPad landscape / small laptop)
- 1366px (laptop)

Pages to check:
1. `/auth/login` — left panel hidden on mobile, form centered
2. `/auth/signup` — same as login
3. `/auth/reset-password` — centered, no overflow
4. `/dashboard/command-center` — grids stack properly
5. `/settings` — delete modal full-width on mobile
6. `/data-deletion` — no horizontal overflow
7. Chat interface — full-screen on mobile

- [ ] **Step 3: Test swipe gesture**

In mobile responsive mode (375px), on any dashboard page:
1. Swipe right from left edge → sidebar opens
2. Swipe left on open sidebar → sidebar closes
3. Tap backdrop → sidebar closes

- [ ] **Step 4: Final commit if any touch-ups needed**

```bash
git add -A
git commit -m "fix: mobile responsiveness touch-ups from visual testing"
```
