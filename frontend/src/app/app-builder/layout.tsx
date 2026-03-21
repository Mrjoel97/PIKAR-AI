import { GsdProgressBar } from '@/components/app-builder/GsdProgressBar';

export default function AppBuilderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50">
      <GsdProgressBar currentStage="questioning" />
      <main className="max-w-3xl mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
}
