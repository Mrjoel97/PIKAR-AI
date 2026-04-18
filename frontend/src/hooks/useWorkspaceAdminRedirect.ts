'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useWorkspace } from '@/contexts/WorkspaceContext';

export const WORKSPACE_ADMIN_ONLY_MESSAGE =
  'This page is for workspace admins. Contact your admin for access.';

export function useWorkspaceAdminRedirect() {
  const router = useRouter();
  const { ready, canManageTeam, isTeamWorkspace } = useWorkspace();
  const redirectedRef = useRef(false);
  const blocked = ready && isTeamWorkspace && !canManageTeam;

  useEffect(() => {
    if (blocked && !redirectedRef.current) {
      redirectedRef.current = true;
      toast.info(WORKSPACE_ADMIN_ONLY_MESSAGE);
      router.replace('/dashboard');
    }
  }, [blocked, router]);

  return {
    ready,
    blocked,
  };
}

export default useWorkspaceAdminRedirect;
