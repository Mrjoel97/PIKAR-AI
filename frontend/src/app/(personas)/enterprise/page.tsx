import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';

export default function EnterprisePage() {
  return (
    <PersonaDashboardLayout
      persona="enterprise"
      title="Enterprise Strategy Suite"
      description="Global oversight, compliance, and strategic intelligence."
      showChat={true}
    />
  );
}
