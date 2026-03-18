import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';

export default function SMEPage() {
  return (
    <PersonaDashboardLayout
      persona="sme"
      title="SME Management Hub"
      description="Optimize departmental efficiency and resource allocation."
      showChat={true}
    />
  );
}
