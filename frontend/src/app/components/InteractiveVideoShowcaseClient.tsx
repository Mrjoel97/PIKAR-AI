'use client';

import dynamic from 'next/dynamic';

// ssr: false is only valid inside Client Components (Next.js App Router rule).
// page.tsx is a Server Component, so this thin wrapper hosts the dynamic import.
const InteractiveVideoShowcase = dynamic(
  () => import('./InteractiveVideoShowcase'),
  { ssr: false }
);

export default InteractiveVideoShowcase;
