// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import PersonaDashboardLayout from '@/components/dashboard/PersonaDashboardLayout';
import { SolopreneurShell } from '@/components/personas/SolopreneurShell';

export default function SolopreneurPage() {
  return (
    <PersonaDashboardLayout
      persona="solopreneur"
      title="Solopreneur Command Center"
      description="Agile tools for rapid execution and growth."
      showChat={true}
      headerContent={<SolopreneurShell headerOnly />}
    />
  );
}
