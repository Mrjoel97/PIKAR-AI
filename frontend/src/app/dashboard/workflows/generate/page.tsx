'use client';

import React from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function WorkflowGeneratorPage() {
    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Workflows', href: '/dashboard/workflows/templates' },
        { label: 'Generator' },
    ];

    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">
                        AI Workflow Generator
                    </h1>
                    <p className="text-slate-500 mt-1">
                        Describe your process and let AI create a workflow
                    </p>
                </div>

                <div className="bg-white p-12 rounded-3xl border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="max-w-md">
                        <h2 className="text-xl font-bold text-slate-800 mb-2">AI Generation Coming Soon</h2>
                        <p className="text-slate-500">
                            Our AI-powered workflow generation interface is currently under development. Soon you'll be able to create complex workflows just by describing them.
                        </p>
                    </div>
                </div>
            </div>
        </PremiumShell>
    );
}
