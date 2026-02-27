'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import { BrainDumpInterface } from '@/components/braindump/BrainDumpInterface';
import { usePersona } from '@/contexts/PersonaContext';

export default function BrainDumpPage() {
    const { persona } = usePersona();
    const resolvedPersona = persona || 'startup';

    return (
        <PersonaDashboardLayout
            persona={resolvedPersona}
            title="Brain Dumps"
            description="Review and manage your recorded ideas and validation plans."
            showChat={false}
        >
            <div className="p-6">
                <BrainDumpInterface />
            </div>
        </PersonaDashboardLayout>
    );
}
