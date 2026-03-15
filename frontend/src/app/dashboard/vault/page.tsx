'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { VaultInterface } from '@/components/vault/VaultInterface';

export default function VaultPage() {
    return (
        <DashboardErrorBoundary fallbackTitle="Vault Error">
            <PremiumShell>
                <div className="min-h-screen bg-white p-6 md:p-10">
                    <VaultInterface />
                </div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
