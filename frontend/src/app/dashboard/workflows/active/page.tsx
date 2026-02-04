'use client';

import React from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function ActiveWorkflowsPage() {
    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Workflows', href: '/dashboard/workflows/templates' },
        { label: 'Active' },
    ];

    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">
                        Ongoing Workflows
                    </h1>
                    <p className="text-slate-500 mt-1">
                        Track and manage your active workflows
                    </p>
                </div>

                <div className="p-12 rounded-3xl border border-slate-100 bg-white/50 flex flex-col items-center justify-center text-center">
                    <p className="text-slate-400 font-medium">
                        Active workflow tracking coming soon
                    </p>
                </div>
            </div>
        </PremiumShell>
    );
}
