'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import WidgetGallery from '@/components/widgets/WidgetGallery';
import { usePersona } from '@/contexts/PersonaContext';

export default function DashboardPage() {
  const router = useRouter();
  const { persona, isLoading, userId } = usePersona();

  // Redirect to persona-specific route when persona is known
  useEffect(() => {
    if (!isLoading && persona) {
      router.replace(`/${persona}`);
    }
  }, [isLoading, persona, router]);

  // Show loading while determining persona
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="animate-pulse text-slate-400 text-sm">Loading your workspace...</div>
      </div>
    );
  }

  // Fallback for users without persona (edge case: persona not set)
  const resolvedPersona = persona || 'startup';
  return (
    <PersonaDashboardLayout
      persona={resolvedPersona}
      title="Dashboard"
      description="Your personalized workspace"
      showChat={false}
    >
      <div className="p-6">
        <h2 className="text-2xl font-bold mb-4 text-slate-900 dark:text-slate-100">Your Widgets</h2>
        {userId && <WidgetGallery userId={userId} />}
      </div>
    </PersonaDashboardLayout>
  );
}
