'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { GsdProgressBar } from '@/components/app-builder/GsdProgressBar';
import { getProject } from '@/services/app-builder';
import type { GsdStage } from '@/types/app-builder';

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams<{ projectId: string }>();
  const projectId = params?.projectId ?? '';
  const [stage, setStage] = useState<GsdStage>('research');

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then((project) => setStage((project.stage as GsdStage) ?? 'research'))
      .catch(() => setStage('research'));
  }, [projectId]);

  return (
    <>
      {projectId && <GsdProgressBar currentStage={stage} />}
      <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
    </>
  );
}
