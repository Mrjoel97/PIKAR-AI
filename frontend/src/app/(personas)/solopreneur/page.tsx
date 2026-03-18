import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';

export default function SolopreneurPage() {
  return (
    <PersonaDashboardLayout
      persona="solopreneur"
      title="Solopreneur Command Center"
      description="Agile tools for rapid execution and growth."
      showChat={true}
    />
  );
}
