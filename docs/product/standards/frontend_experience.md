# Frontend Experience Standards

## 1. Design & Aesthetics (`frontend-design`, `ui-ux-pro-max`)
**Goal:** Distinctive, production-grade interfaces. No "AI Slop".

-   **Aesthetic Direction:** Commit to a BOLD direction (Minimal, Maximalist, Industrial).
-   **Typography:** Use distinctive fonts (avoid generic Inter/Roboto if possible, or use them with specific intent).
-   **Visuals:**
    -   **Nano Banana:** Use AI prompts to generate high-fidelity, surreal/artistic assets. Avoid stock photos.
    -   **Motion:** High-impact staggered reveals. Use `framer-motion` or CSS animations.
-   **Accessibility:**
    -   Contrast ratio > 4.5:1.
    -   Touch targets > 44px (`min-h-[44px]`).
    -   Focus states must be visible.

## 2. React Modernization (`react-modernization`)
**Goal:** Maintainable, high-performance React code.

-   **Functional Components Only:** No Class Components.
-   **Hooks:** Use `useState`, `useEffect`, `useContext`.
    -   *Migration:* Convert any legacy class components encountered.
-   **Concurrent Features:** Use `Suspense` and `Transitions` for non-urgent updates.
-   **Strict Mode:** Ensure app runs without warnings in Strict Mode.

## 3. Performance (`vercel-react-best-practices`)
**Goal:** Core Web Vitals optimized.

-   **No Waterfalls:**
    -   **Bad:** `await A(); await B();`
    -   **Good:** `await Promise.all([A(), B()]);`
-   **Bundle Size:**
    -   **No Barrel Exports:** Import `from 'lib/button'` not `from 'lib'`.
    -   **Dynamic Imports:** Use `next/dynamic` for heavy components (charts, 3D).
-   **Server Components:** Default to RSC. Use `"use client"` only for interaction.

## 4. Immersive Media
-   **3D Scenes (`threejs-fundamentals`):**
    -   Use `react-three-fiber` where applicable.
    -   Optimize: Reuse geometries/materials, use `useFrame` cautiously.
-   **Video (`remotion`):**
    -   Use `useCurrentFrame` for all animations.
    -   Think in seconds * fps.
