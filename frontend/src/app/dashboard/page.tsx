import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import WidgetGallery from '@/components/widgets/WidgetGallery';

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect('/auth/login');

  // Fetch user persona to setup dashboard correctly
  const { data: agentProfile } = await supabase
    .from('user_executive_agents')
    .select('persona')
    .eq('user_id', user.id)
    .single();

  const persona = agentProfile?.persona || 'startup';

  return (
    <PersonaDashboardLayout
      persona={persona}
      title="Dashboard"
      description="Your personalized workspace"
      showChat={true}
    >
      <div className="p-6">
        <h2 className="text-2xl font-bold mb-4 text-slate-900 dark:text-slate-100">Your Widgets</h2>
        <WidgetGallery userId={user.id} />
      </div>
    </PersonaDashboardLayout>
  );
}
