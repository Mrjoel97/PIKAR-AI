'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { ReportsInterface } from '@/components/reports/ReportsInterface';

export default function ReportsPage() {
    return (
        <DashboardErrorBoundary fallbackTitle="Reports Error">
            <PremiumShell>
                <ReportsInterface />
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
