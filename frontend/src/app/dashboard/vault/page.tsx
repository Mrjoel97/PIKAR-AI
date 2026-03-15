'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { VaultInterface } from '@/components/vault/VaultInterface';

export default function VaultPage() {
    return (
        <DashboardErrorBoundary fallbackTitle="Vault Error">
            <PremiumShell>
                <VaultInterface />
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
