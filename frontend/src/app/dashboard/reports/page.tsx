'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import { ReportsInterface } from '@/components/reports/ReportsInterface';

export default function ReportsPage() {
    return (
        <PremiumShell>
            <div className="min-h-screen bg-white p-6 md:p-10">
                <ReportsInterface />
            </div>
        </PremiumShell>
    );
}
