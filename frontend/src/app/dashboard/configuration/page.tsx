import { PremiumShell } from '@/components/layout/PremiumShell';

export default function ConfigurationPage() {
    return (
        <PremiumShell>
            <div className="space-y-6">
                <h1 className="text-2xl font-bold font-outfit text-slate-800">Configuration</h1>
                <p className="text-slate-500">Manage your persona and application settings here.</p>
                {/* Placeholder for configuration settings */}
                <div className="p-8 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-slate-400">
                    Configuration Settings Coming Soon
                </div>
            </div>
        </PremiumShell>
    );
}
