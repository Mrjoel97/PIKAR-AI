'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import WidgetGallery from '@/components/widgets/WidgetGallery';
import { usePersona } from '@/contexts/PersonaContext';

export default function DashboardPage() {
  // Middleware already validates auth and redirects /dashboard -> /{persona}.
  // Use cached context instead of blocking server-side DB calls.
  const { persona, userId } = usePersona();
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
