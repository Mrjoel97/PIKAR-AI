'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function ProjectPage() {
  const router = useRouter();
  const params = useParams<{ projectId: string }>();

  useEffect(() => {
    router.replace(`/app-builder/${params.projectId}/research`);
  }, [router, params.projectId]);

  return (
    <div className="flex items-center justify-center py-20 text-slate-400">
      Loading...
    </div>
  );
}
