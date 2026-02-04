'use client';

import React from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function NewInitiativePage() {
    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Initiatives' },
        { label: 'New' },
    ];

    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">
                        Create Initiative
                    </h1>
                    <p className="text-slate-500 mt-1">
                        Launch a new strategic project
                    </p>
                </div>

                <div className="bg-white p-12 rounded-3xl border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <p className="text-slate-400 font-medium">
                        Initiative creation form coming soon
                    </p>
                </div>
            </div>
        </PremiumShell>
    );
}
