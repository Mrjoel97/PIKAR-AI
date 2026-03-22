import { GsdProgressBar } from '@/components/app-builder/GsdProgressBar';
import type { GsdStage } from '@/types/app-builder';

/** Server-side fetch to get the project's current GSD stage. */
async function fetchProjectStage(projectId: string): Promise<GsdStage> {
  try {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}`, {
      cache: 'no-store',
    });
    if (!res.ok) return 'research';
    const project = await res.json();
    return (project.stage as GsdStage) ?? 'research';
  } catch {
    return 'research';
  }
}

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const stage = await fetchProjectStage(projectId);

  return (
    <>
      <GsdProgressBar currentStage={stage} />
      <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
    </>
  );
}
