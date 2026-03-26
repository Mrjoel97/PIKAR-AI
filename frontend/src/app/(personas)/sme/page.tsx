// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import { SmeShell } from '@/components/personas/SmeShell';

export default function SMEPage() {
  return (
    <PersonaDashboardLayout
      persona="sme"
      title="SME Management Hub"
      description="Optimize departmental efficiency and resource allocation."
      showChat={true}
      headerContent={<SmeShell headerOnly />}
    />
  );
}
