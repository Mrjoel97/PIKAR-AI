// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { AdminSidebar } from '@/components/admin/AdminSidebar';
import { AdminChatPanel } from '@/components/admin/AdminChatPanel';

/**
 * Admin layout with server-side access guard.
 * Fetches /admin/check-access with the user's Bearer token.
 * Non-admin users are redirected to the main app before any admin UI renders.
 */
export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect('/login');
  }

  // Enforce stricter session timeout for admin (default 30 min)
  const adminTimeoutMs = Number(process.env.ADMIN_SESSION_TIMEOUT_MS) || 30 * 60 * 1000;
  const sessionAge = Date.now() - new Date(session.expires_at! * 1000 - 3600 * 1000).getTime();
  if (sessionAge > adminTimeoutMs) {
    await supabase.auth.signOut();
    redirect('/login');
  }

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  let adminEmail: string | undefined;

  try {
    const res = await fetch(`${API_URL}/admin/check-access`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        'X-Admin-Client': 'pikar-admin/1.0',
      },
      cache: 'no-store',
    });

    if (!res.ok) {
      await supabase.auth.signOut();
      redirect('/login?error=Access+denied.+Admin+privileges+required.');
    }

    const data = (await res.json()) as { access: boolean; email?: string };
    if (!data.access) {
      await supabase.auth.signOut();
      redirect('/login?error=Access+denied.+Admin+privileges+required.');
    }
    adminEmail = data.email;
  } catch {
    // Network error or fetch failure — deny access
    redirect('/login?error=Unable+to+verify+admin+access.');
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      <AdminSidebar adminEmail={adminEmail} />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
      <AdminChatPanel />
    </div>
  );
}
