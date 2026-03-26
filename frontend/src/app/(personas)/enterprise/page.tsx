// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import { EnterpriseShell } from '@/components/personas/EnterpriseShell';

export default function EnterprisePage() {
  return (
    <PersonaDashboardLayout
      persona="enterprise"
      title="Enterprise Strategy Suite"
      description="Global oversight, compliance, and strategic intelligence."
      showChat={true}
      headerContent={<EnterpriseShell headerOnly />}
    />
  );
}
