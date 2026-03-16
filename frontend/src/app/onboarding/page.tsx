'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getOnboardingStatus } from '@/services/onboarding';
import { OnboardingChat } from './components/OnboardingChat';

export default function OnboardingPage() {
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await getOnboardingStatus();
        if (status.is_completed) {
          router.replace('/dashboard/command-center');
          return;
        }
        setIsReady(true);
      } catch {
        // If status check fails, show onboarding anyway (new user)
        setIsReady(true);
      } finally {
        setIsLoading(false);
      }
    };

    checkStatus();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-teal-600 to-teal-700 text-white flex items-center justify-center shadow-lg shadow-teal-500/25 animate-pulse">
            <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
            </svg>
          </div>
          <span className="text-sm text-slate-400">Preparing your experience...</span>
        </div>
      </div>
    );
  }

  if (!isReady) return null;

  return <OnboardingChat />;
}
