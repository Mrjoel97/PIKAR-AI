'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { ActiveWorkspace } from '@/components/dashboard/ActiveWorkspace';
import { PERSONA_INFO, PersonaType } from '@/services/onboarding';
import { usePersona } from '@/contexts/PersonaContext';

export default function WorkspacePage() {
    // Middleware already validates auth. Use cached context for instant render.
    const { persona: ctxPersona, userId } = usePersona();
    const persona = (ctxPersona as PersonaType) || 'startup';
    const info = PERSONA_INFO[persona] || PERSONA_INFO['startup'];

    return (
        <DashboardErrorBoundary fallbackTitle="Workspace Error">
            <PersonaDashboardLayout
                persona={persona}
                title={info.title}
                description={info.description}
                showChat={true}
            >
                {userId && <ActiveWorkspace user={{ id: userId }} persona={persona} />}
            </PersonaDashboardLayout>
        </DashboardErrorBoundary>
    );
}
