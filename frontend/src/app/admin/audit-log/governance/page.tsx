// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Admin Governance Audit Log page (Phase 49 Plan 05 — AUTH-05).
 *
 * Sibling page to /admin/audit-log (which shows admin_audit_log — admin-only
 * actions). This page shows governance_audit_log — the user-action audit
 * trail populated by AuditLogMiddleware (Phase 49 Plan 04).
 *
 * The page inherits the server-side `require_admin` guard from
 * frontend/src/app/(admin)/layout.tsx; non-admins are redirected before
 * this page ever renders.
 */

import Link from 'next/link';

import { GovernanceAuditTable } from '@/components/admin/GovernanceAuditTable';

export const metadata = {
  title: 'Governance Audit Log | Admin',
  description: 'User-action audit trail across the Pikar-AI platform.',
};

export default function GovernanceAuditLogPage() {
  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-100">
          Governance Audit Log
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          User actions across the platform. Filter by user, action type, or
          date range. For admin-only actions, see the{' '}
          <Link
            href="/admin/audit-log"
            className="text-indigo-400 underline hover:text-indigo-300"
          >
            Admin Audit Log
          </Link>
          .
        </p>
      </div>
      <GovernanceAuditTable />
    </div>
  );
}
