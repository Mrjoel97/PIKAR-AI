import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { getResend, FROM_ADDRESS } from '@/lib/resend';
import { getClientIp, rateLimiters } from '@/lib/rate-limit';
import TeamInviteEmail from '../../../../../emails/team-invite';

const API_BASE_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type InviteRole = 'admin' | 'member' | 'viewer';

type InviteRequestBody = {
  email?: unknown;
  role?: unknown;
  workspaceId?: unknown;
  inviteId?: unknown;
  inviteToken?: unknown;
  inviteExpiresAt?: unknown;
};

type BackendWorkspaceResponse = {
  id: string;
  name: string;
};

type BackendInviteResponse = {
  id: string;
  token: string;
  role: string;
  expires_at: string;
};

function isInviteRole(value: unknown): value is InviteRole {
  return value === 'admin' || value === 'member' || value === 'viewer';
}

function normalizeEmail(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }

  const trimmed = value.trim().toLowerCase();
  if (!trimmed || !EMAIL_PATTERN.test(trimmed)) {
    return null;
  }

  return trimmed;
}

function normalizeOptionalString(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function getInviterName(user: { email?: string | null; user_metadata?: Record<string, unknown> } | null) {
  const metadata = (user?.user_metadata ?? {}) as Record<string, unknown>;
  const fullName = metadata.full_name;
  const name = metadata.name;

  if (typeof fullName === 'string' && fullName.trim()) {
    return fullName.trim();
  }

  if (typeof name === 'string' && name.trim()) {
    return name.trim();
  }

  if (typeof user?.email === 'string' && user.email.includes('@')) {
    return user.email.split('@')[0];
  }

  return 'A teammate';
}

function toErrorResponse(message: string, status: number) {
  return NextResponse.json({ error: message }, { status });
}

export async function POST(request: NextRequest) {
  const rl = rateLimiters.authenticated.check(getClientIp(request));
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests. Please try again later.' },
      { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } },
    );
  }

  try {
    const body = (await request.json()) as InviteRequestBody;
    const email = normalizeEmail(body.email);
    const inviteId = normalizeOptionalString(body.inviteId);
    const inviteToken = normalizeOptionalString(body.inviteToken);
    const inviteExpiresAt = normalizeOptionalString(body.inviteExpiresAt);
    const workspaceId =
      typeof body.workspaceId === 'string' && body.workspaceId.trim()
        ? body.workspaceId.trim()
        : null;

    if (!email) {
      return toErrorResponse('Please provide a valid email address.', 400);
    }

    if (!workspaceId) {
      return toErrorResponse('Workspace ID is required.', 400);
    }

    if (!isInviteRole(body.role)) {
      return toErrorResponse('Role must be admin, member, or viewer.', 400);
    }

    const supabase = await createClient();
    const [
      {
        data: { user },
      },
      {
        data: { session },
      },
    ] = await Promise.all([
      supabase.auth.getUser(),
      supabase.auth.getSession(),
    ]);

    if (!user || !session?.access_token) {
      return toErrorResponse('Not authenticated.', 401);
    }

    const workspaceResponse = await fetch(`${API_BASE_URL}/teams/workspace`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
      cache: 'no-store',
    });

    if (!workspaceResponse.ok) {
      const workspaceError = await workspaceResponse.json().catch(() => ({}));
      const message =
        typeof workspaceError?.detail === 'string'
          ? workspaceError.detail
          : 'Failed to resolve workspace context.';
      return toErrorResponse(message, workspaceResponse.status);
    }

    const workspace = (await workspaceResponse.json()) as BackendWorkspaceResponse;
    if (workspace.id !== workspaceId) {
      return toErrorResponse('Workspace mismatch. Please refresh and try again.', 400);
    }

    let invite: BackendInviteResponse;
    if (inviteToken) {
      const fallbackExpiry = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
      invite = {
        id: inviteId ?? `resend-${Date.now()}`,
        token: inviteToken,
        role: body.role === 'member' ? 'editor' : body.role,
        expires_at: inviteExpiresAt ?? fallbackExpiry,
      };
    } else {
      const backendRole = body.role === 'member' ? 'editor' : body.role;
      const inviteResponse = await fetch(`${API_BASE_URL}/teams/invites`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          role: backendRole,
          expires_hours: 168,
          invited_email: email,
        }),
      });

      if (!inviteResponse.ok) {
        const inviteError = await inviteResponse.json().catch(() => ({}));
        const message =
          typeof inviteError?.detail === 'string'
            ? inviteError.detail
            : 'Failed to create invite.';
        return toErrorResponse(message, inviteResponse.status);
      }

      invite = (await inviteResponse.json()) as BackendInviteResponse;
    }

    const inviterName = getInviterName(user);
    const roleLabel =
      body.role === 'admin' ? 'Admin' : body.role === 'viewer' ? 'Viewer' : 'Member';

    const acceptUrl = `${request.nextUrl.origin}/invite/${invite.token}`;
    const resend = getResend();
    const emailResult = await resend.emails.send(
      {
        from: FROM_ADDRESS,
        to: email,
        subject: `${inviterName} invited you to join ${workspace.name} on Pikar AI`,
        react: TeamInviteEmail({
          inviterName,
          workspaceName: workspace.name,
          role: roleLabel,
          acceptUrl,
        }),
      },
      {
        headers: {
          'Idempotency-Key': `team-invite-${invite.id}`,
        },
      },
    );

    if (emailResult.error) {
      console.error('[api/teams/invite] Invite email send failed:', emailResult.error);
      return toErrorResponse('Invite created, but the email could not be sent.', 500);
    }

    return NextResponse.json({
      success: true,
      invite: {
        id: invite.id,
        role: body.role,
        expires_at: invite.expires_at,
      },
    });
  } catch (error) {
    console.error('[api/teams/invite] Unexpected error:', error);
    return toErrorResponse('Failed to send invite.', 500);
  }
}
