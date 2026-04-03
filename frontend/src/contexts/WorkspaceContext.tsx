'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { createClient } from '@/lib/supabase/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WorkspaceRole = 'admin' | 'editor' | 'viewer' | null;

export interface WorkspaceMember {
  id: string;
  user_id: string;
  email: string;
  display_name: string | null;
  role: string;
  joined_at: string;
}

export interface WorkspaceState {
  /** Whether the initial load has completed. */
  ready: boolean;
  /** Current workspace ID, null if no workspace (solo user or free tier). */
  workspaceId: string | null;
  /** Workspace display name. */
  workspaceName: string | null;
  /** Current user's role in the workspace. */
  role: WorkspaceRole;
  /** Number of members in the workspace. */
  memberCount: number;
  /** Whether current user is the workspace owner. */
  isOwner: boolean;

  /** Permission check helpers */
  canEdit: boolean;       // admin or editor
  canManageTeam: boolean; // admin only
  canView: boolean;       // any role (admin, editor, viewer)
  isTeamWorkspace: boolean; // workspace has >1 member

  /** Refresh workspace state from API. */
  refresh: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceState | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState<string | null>(null);
  const [role, setRole] = useState<WorkspaceRole>(null);
  const [memberCount, setMemberCount] = useState(0);
  const [isOwner, setIsOwner] = useState(false);
  const initRef = useRef(false);

  // ── Derived permission booleans ──────────────────────────────────────────
  //
  // When role is null (solo user — no workspace yet), we default all
  // permissions to true so solo users are never blocked. The RBAC system
  // only restricts once a workspace membership row exists.
  const hasNoWorkspace = role === null;
  const canEdit = hasNoWorkspace || role === 'admin' || role === 'editor';
  const canManageTeam = hasNoWorkspace || role === 'admin';
  const canView = true; // always — even viewer role can view
  const isTeamWorkspace = memberCount > 1;

  // ── Load workspace from Supabase ─────────────────────────────────────────
  const loadWorkspace = useCallback(async () => {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      setWorkspaceId(null);
      setWorkspaceName(null);
      setRole(null);
      setMemberCount(0);
      setIsOwner(false);
      return;
    }

    try {
      // Query workspace_members joined with workspaces for the current user.
      const { data: memberRows, error: memberError } = await supabase
        .from('workspace_members')
        .select('id, role, joined_at, workspace_id, workspaces(id, name, slug, owner_id)')
        .eq('user_id', user.id)
        .limit(1);

      if (memberError || !memberRows || memberRows.length === 0) {
        // No workspace yet — solo user state. All permissions default to true.
        setWorkspaceId(null);
        setWorkspaceName(null);
        setRole(null);
        setMemberCount(0);
        setIsOwner(false);
        return;
      }

      const membership = memberRows[0];
      const workspace = membership.workspaces as { id: string; name: string; slug: string | null; owner_id: string } | null;

      if (!workspace) {
        setWorkspaceId(null);
        setWorkspaceName(null);
        setRole(null);
        setMemberCount(0);
        setIsOwner(false);
        return;
      }

      const wsId = workspace.id;

      // Count all members in this workspace.
      const { count: memberCountResult } = await supabase
        .from('workspace_members')
        .select('id', { count: 'exact', head: true })
        .eq('workspace_id', wsId);

      setWorkspaceId(wsId);
      setWorkspaceName(workspace.name);
      setRole(membership.role as WorkspaceRole);
      setMemberCount(memberCountResult ?? 1);
      setIsOwner(workspace.owner_id === user.id);
    } catch {
      // Graceful degradation: table may not exist during migration rollout,
      // or the user may be on the free tier without a workspace. Fall back
      // to solo-user defaults so no UI is blocked.
      setWorkspaceId(null);
      setWorkspaceName(null);
      setRole(null);
      setMemberCount(0);
      setIsOwner(false);
    }
  }, []);

  // ── Bootstrap ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    loadWorkspace().finally(() => setReady(true));

    // React to auth state changes.
    const supabase = createClient();
    const { data: { subscription: authSub } } = supabase.auth.onAuthStateChange(
      async (_event: string, session: { user: { id: string } } | null) => {
        if (session?.user) {
          await loadWorkspace();
        } else {
          setWorkspaceId(null);
          setWorkspaceName(null);
          setRole(null);
          setMemberCount(0);
          setIsOwner(false);
        }
      },
    );

    return () => {
      authSub.unsubscribe();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Refresh ──────────────────────────────────────────────────────────────
  const refresh = useCallback(async () => {
    await loadWorkspace();
  }, [loadWorkspace]);

  return (
    <WorkspaceContext.Provider
      value={{
        ready,
        workspaceId,
        workspaceName,
        role,
        memberCount,
        isOwner,
        canEdit,
        canManageTeam,
        canView,
        isTeamWorkspace,
        refresh,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error('useWorkspace must be used within a <WorkspaceProvider>');
  }
  return ctx;
}
