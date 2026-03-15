'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import { VaultInterface } from '@/components/vault/VaultInterface';

export default function VaultPage() {
    return (
        <PremiumShell>
            <div className="min-h-screen bg-white p-6 md:p-10">
                <VaultInterface />
            </div>
        </PremiumShell>
    );
}
