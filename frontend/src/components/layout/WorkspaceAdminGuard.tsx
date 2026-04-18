'use client';

import React from 'react';
import { useWorkspaceAdminRedirect } from '@/hooks/useWorkspaceAdminRedirect';

interface WorkspaceAdminGuardProps {
  children: React.ReactNode;
}

export function WorkspaceAdminGuard({
  children,
}: WorkspaceAdminGuardProps) {
  const { ready, blocked } = useWorkspaceAdminRedirect();

  if (!ready || blocked) {
    return null;
  }

  return <>{children}</>;
}

export default WorkspaceAdminGuard;
