'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { PersonaType, PERSONA_INFO } from '@/services/onboarding';
import {
  submitBusinessContext,
  submitPreferences,
  submitAgentSetup,
  completeOnboarding,
  type BusinessContextInput,
  type UserPreferencesInput,
  type AgentSetupInput,
} from '@/services/onboarding';

interface OnboardingTransitionProps {
  agentName: string;
  persona: PersonaType;
  firstAction: string;
  extractedContext: Record<string, unknown> | null;
  preferences: { tone: string; verbosity: string } | null;
  onComplete: () => void;
}

const STEPS = [
  { label: 'Saving your business profile', icon: '📋' },
  { label: 'Configuring AI persona', icon: '🤖' },
  { label: 'Setting up your workspace', icon: '🏗️' },
  { label: 'Preparing your dashboard', icon: '✨' },
];

// Map first action prompts to focus areas
const ACTION_TO_FOCUS: Record<string, string[]> = {
  revenue_strategy: ['finance', 'strategy'],
  brain_dump: ['strategy', 'operations'],
  weekly_plan: ['operations', 'strategy'],
  growth_experiment: ['marketing', 'strategy'],
  pitch_review: ['strategy', 'content'],
  burn_rate: ['finance', 'operations'],
  dept_health: ['operations', 'hr'],
  process_audit: ['operations', 'strategy'],
  compliance_review: ['operations', 'finance'],
  stakeholder_briefing: ['strategy', 'operations'],
  risk_assessment: ['operations', 'finance'],
  portfolio_review: ['strategy', 'finance'],
};

export function OnboardingTransition({
  agentName,
  persona,
  firstAction,
  extractedContext,
  preferences,
  onComplete,
}: OnboardingTransitionProps) {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  const info = PERSONA_INFO[persona];

  const runOnboarding = useCallback(async () => {
    try {
      // Step 1: Submit business context
      setCurrentStep(0);
      const context: BusinessContextInput = {
        company_name: (extractedContext?.company_name as string) || 'My Business',
        industry: (extractedContext?.industry as string) || 'Other',
        description: (extractedContext?.description as string) || '',
        goals: (extractedContext?.goals as string[]) || ['growth'],
        team_size: (extractedContext?.team_size as string) || 'startup',
        role: (extractedContext?.role as string) || 'founder',
        website: (extractedContext?.website as string) || undefined,
      };
      await submitBusinessContext(context);

      await new Promise((r) => setTimeout(r, 600));

      // Step 2: Submit preferences
      setCurrentStep(1);
      const prefs: UserPreferencesInput = {
        tone: preferences?.tone || 'professional',
        verbosity: preferences?.verbosity || 'balanced',
        communication_style: 'direct',
        notification_frequency: 'daily',
      };
      await submitPreferences(prefs);

      await new Promise((r) => setTimeout(r, 600));

      // Step 3: Submit agent setup
      setCurrentStep(2);
      // Determine focus areas from the first action selection
      const focusKey = Object.keys(ACTION_TO_FOCUS).find((key) =>
        firstAction.toLowerCase().includes(key.replace('_', ' '))
      );
      const focusAreas = focusKey ? ACTION_TO_FOCUS[focusKey] : ['strategy', 'operations'];

      const setup: AgentSetupInput = {
        agent_name: agentName || 'Atlas',
        focus_areas: focusAreas,
      };
      await submitAgentSetup(setup);

      await new Promise((r) => setTimeout(r, 600));

      // Step 4: Complete onboarding
      setCurrentStep(3);
      await completeOnboarding();

      await new Promise((r) => setTimeout(r, 800));

      // Done!
      setIsComplete(true);
      onComplete(); // Clear session storage

      // Navigate to dashboard with first action as initial prompt
      setTimeout(() => {
        const encodedPrompt = encodeURIComponent(firstAction);
        router.push(`/dashboard/command-center?initialPrompt=${encodedPrompt}`);
      }, 1500);

    } catch (err) {
      console.error('Onboarding completion failed:', err);
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    }
  }, [agentName, extractedContext, preferences, firstAction, onComplete, router]);

  useEffect(() => {
    runOnboarding();
  }, [runOnboarding]);

  const handleRetry = () => {
    setError(null);
    setCurrentStep(0);
    runOnboarding();
  };

  if (error) {
    return (
      <div className="max-w-md mx-auto text-center p-6">
        <div className="text-4xl mb-4">😔</div>
        <h3 className="text-lg font-semibold text-slate-800 mb-2">
          Hit a small snag
        </h3>
        <p className="text-sm text-slate-500 mb-6">{error}</p>
        <button
          onClick={handleRetry}
          className="px-6 py-3 bg-teal-600 text-white rounded-xl font-semibold text-sm hover:bg-teal-700 transition-all"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900 rounded-2xl p-8 shadow-2xl">
        {/* Agent name and persona */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-3 animate-pulse">{info.icon}</div>
          <h3 className="text-xl font-bold text-white mb-1">
            {isComplete ? `${agentName} is ready!` : `${agentName} is getting ready...`}
          </h3>
          <p className="text-sm text-slate-400">
            {isComplete
              ? 'Your personalized workspace is all set'
              : 'Setting up your personalized experience'}
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-4">
          {STEPS.map((step, i) => {
            const isActive = i === currentStep && !isComplete;
            const isDone = i < currentStep || isComplete;

            return (
              <div
                key={i}
                className={`flex items-center gap-3 transition-all duration-500 ${
                  isDone ? 'opacity-100' : isActive ? 'opacity-100' : 'opacity-40'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-500 ${
                    isDone
                      ? 'bg-teal-500 text-white'
                      : isActive
                        ? 'bg-teal-500/20 text-teal-400 animate-pulse'
                        : 'bg-slate-700 text-slate-500'
                  }`}
                >
                  {isDone ? (
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <span className="text-sm">{step.icon}</span>
                  )}
                </div>
                <span className={`text-sm font-medium ${isDone ? 'text-white' : isActive ? 'text-teal-300' : 'text-slate-500'}`}>
                  {step.label}
                </span>
                {isActive && (
                  <svg className="animate-spin w-4 h-4 text-teal-400 ml-auto" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                )}
              </div>
            );
          })}
        </div>

        {/* Completion celebration */}
        {isComplete && (
          <div className="mt-8 text-center animate-[fadeInUp_0.5s_ease-out_both]">
            <div className="text-3xl mb-2">🎉</div>
            <p className="text-sm text-teal-300 font-medium">
              Redirecting to your dashboard...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
