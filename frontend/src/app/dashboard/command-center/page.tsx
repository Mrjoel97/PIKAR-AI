import { createClient } from '@/lib/supabase/server';
import { PERSONA_INFO, PersonaType } from '@/services/onboarding';
import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import { redirect } from 'next/navigation';

export default async function CommandCenterPage() {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        redirect('/auth/login');
    }

    // Fetch persona configuration
    const { data: agentProfile } = await supabase
        .from('user_executive_agents')
        .select('persona, agent_name')
        .eq('user_id', user.id)
        .single() as { data: any, error: any };

    const persona = agentProfile?.persona as PersonaType || 'startup';
    const info = PERSONA_INFO[persona] || PERSONA_INFO['startup'];

    return (
        <PersonaDashboardLayout
            persona={persona}
            title={info.title}
            description={info.description}
            agentName={agentProfile?.agent_name || undefined}
            showChat={false}
        />
    );
}
