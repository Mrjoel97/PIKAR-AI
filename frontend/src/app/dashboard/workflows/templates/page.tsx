'use client';

import React from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function WorkflowTemplatesPage() {
    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Workflows', href: '/dashboard/workflows/templates' },
        { label: 'Templates' },
    ];

    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">
                        Workflow Templates
                    </h1>
                    <p className="text-slate-500 mt-1">
                        Browse and use pre-built workflow templates
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div className="p-8 rounded-3xl border border-dashed border-slate-200 flex items-center justify-center bg-slate-50/50">
                        <span className="text-slate-400 font-medium">
                            Template library coming soon
                        </span>
                    </div>
                </div>
            </div>
        </PremiumShell>
    );
}
