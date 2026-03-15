'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { BrainDumpInterface } from '@/components/braindump/BrainDumpInterface';
import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';

export default function BrainDumpPage() {
    return (
        <DashboardErrorBoundary fallbackTitle="Brain Dump Error">
        <PremiumShell>
            <div className="space-y-6">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="flex items-center gap-4"
                >
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-400 to-purple-500 shadow-lg shadow-violet-200">
                        <Brain className="h-6 w-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                            Brain Dumps
                        </h1>
                        <p className="mt-0.5 text-sm text-slate-500">
                            Turn chaotic thoughts into structured, actionable plans.
                        </p>
                    </div>
                </motion.div>

                {/* Brain Dump Interface */}
                <motion.div
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                >
                    <BrainDumpInterface />
                </motion.div>
            </div>
        </PremiumShell>
        </DashboardErrorBoundary>
    );
}
