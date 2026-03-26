// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import { StartupShell } from '@/components/personas/StartupShell';

export default function StartupPage() {
  return (
    <PersonaDashboardLayout
      persona="startup"
      title="Startup Growth Engine"
      description="Scale your operations and accelerate product-market fit."
      showChat={true}
      headerContent={<StartupShell headerOnly />}
    />
  );
}
