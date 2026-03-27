// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { AdminSidebar } from '@/components/admin/AdminSidebar';
import { AdminChatPanel } from '@/components/admin/AdminChatPanel';

/**
 * Admin layout with server-side access guard.
 * Fetches /admin/check-access with the user's Bearer token.
 * Non-admin users are redirected to /dashboard before any admin UI renders.
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
    redirect('/auth/login');
  }

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  let adminEmail: string | undefined;

  try {
    const res = await fetch(`${API_URL}/admin/check-access`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
      cache: 'no-store',
    });

    if (!res.ok) {
      redirect('/dashboard');
    }

    const data = (await res.json()) as { access: boolean; email?: string };
    if (!data.access) {
      redirect('/dashboard');
    }
    adminEmail = data.email;
  } catch {
    // Network error or fetch failure — deny access
    redirect('/dashboard');
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
