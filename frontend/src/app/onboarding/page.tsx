'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getOnboardingStatus } from '@/services/onboarding';

export default function OnboardingPage() {
    const router = useRouter();

    useEffect(() => {
        const checkStatusAndRedirect = async () => {
            try {
                const status = await getOnboardingStatus();
                
                // Redirect based on progress
                if (status.is_completed) {
                    router.replace('/dashboard/command-center');
                } else if (status.agent_setup_completed) {
                    router.replace('/onboarding/processing');
                } else if (status.preferences_completed) {
                    router.replace('/onboarding/agent-setup');
                } else if (status.business_context_completed) {
                    router.replace('/onboarding/preferences');
                } else {
                    router.replace('/onboarding/business-context');
                }
            } catch {
                // If status check fails, start from beginning
                router.replace('/onboarding/business-context');
            }
        };

        checkStatusAndRedirect();
    }, [router]);

    return (
        <div className="flex items-center justify-center min-h-[50vh]">
            <div className="flex items-center gap-3 text-slate-500">
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Loading...</span>
            </div>
        </div>
    );
}
