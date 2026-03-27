'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { ReportsInterface } from '@/components/reports/ReportsInterface';

export default function ReportsPage() {
    return (
        <DashboardErrorBoundary fallbackTitle="Reports Error">
            <PremiumShell>
                <div className="min-h-screen bg-white p-6 md:p-10">
                    <ReportsInterface />
                </div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
