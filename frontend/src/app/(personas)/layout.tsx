'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// frontend/src/app/(personas)/layout.tsx
import { usePathname } from 'next/navigation';
import { RootErrorBoundary } from '@/components/errors/RootErrorBoundary';

export default function PersonaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  return (
    <section>
      {/* Per-persona error boundary — auto-resets when the user navigates
          between persona routes (pathname change). Keeps the root layout's
          providers mounted when a single persona dashboard crashes.
          See plan 49-02 (AUTH-02). */}
      <RootErrorBoundary
        resetKeys={[pathname]}
        fallbackTitle="This page hit a snag"
      >
        {children}
      </RootErrorBoundary>
    </section>
  );
}
