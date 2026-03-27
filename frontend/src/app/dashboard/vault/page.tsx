'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


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
