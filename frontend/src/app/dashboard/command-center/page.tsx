'use client';

import { PERSONA_INFO, PersonaType } from '@/services/onboarding';
import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { usePersona } from '@/contexts/PersonaContext';

export default function CommandCenterPage() {
    // Middleware already validates auth. Use cached context for instant render.
    const { persona: ctxPersona } = usePersona();
    const persona = (ctxPersona as PersonaType) || 'startup';
    const info = PERSONA_INFO[persona] || PERSONA_INFO['startup'];

    return (
        <DashboardErrorBoundary fallbackTitle="Command Center Error">
            <PersonaDashboardLayout
                persona={persona}
                title={info.title}
                description={info.description}
                showChat={false}
            />
        </DashboardErrorBoundary>
    );
}
