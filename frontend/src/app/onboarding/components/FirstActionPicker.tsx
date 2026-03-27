'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { PersonaType } from '@/services/onboarding';

interface FirstActionPickerProps {
  persona: PersonaType;
  onSelect: (actionId: string, actionPrompt: string) => void;
}

interface ActionOption {
  id: string;
  icon: string;
  title: string;
  description: string;
  prompt: string; // The initial prompt to pass to dashboard chat
}

const PERSONA_ACTIONS: Record<PersonaType, ActionOption[]> = {
  solopreneur: [
    {
      id: 'revenue_strategy',
      icon: '💰',
      title: 'Map My Revenue Strategy',
      description: 'Let\'s figure out your best path to consistent income',
      prompt: 'Help me map out a revenue strategy for my business. I want to identify my best income opportunities and create a plan to grow consistently.',
    },
    {
      id: 'brain_dump',
      icon: '🧠',
      title: 'Brain Dump Everything',
      description: 'Get all your ideas out of your head and organized',
      prompt: 'I want to do a brain dump. Help me get all my ideas, tasks, and thoughts organized so I can focus on what matters most.',
    },
    {
      id: 'weekly_plan',
      icon: '📋',
      title: 'Plan My Week',
      description: 'Create a focused action plan for the next 7 days',
      prompt: 'Help me create a focused weekly plan. What should I prioritize this week to make the most progress on my business?',
    },
  ],
  startup: [
    {
      id: 'growth_experiment',
      icon: '🚀',
      title: 'Design a Growth Experiment',
      description: 'Test a hypothesis to accelerate your growth',
      prompt: 'Help me design a growth experiment. I want to identify a hypothesis we can test quickly to learn what drives growth for our startup.',
    },
    {
      id: 'pitch_review',
      icon: '🎯',
      title: 'Review My Pitch',
      description: 'Sharpen your story for investors or customers',
      prompt: 'I want to work on my pitch. Help me sharpen our value proposition and story for investors and customers.',
    },
    {
      id: 'burn_rate',
      icon: '📊',
      title: 'Check My Burn Rate',
      description: 'Understand your runway and financial health',
      prompt: 'Help me analyze our burn rate and runway. I want to understand our financial health and make smart spending decisions.',
    },
  ],
  sme: [
    {
      id: 'dept_health',
      icon: '🏥',
      title: 'Department Health Check',
      description: 'See how each department is performing',
      prompt: 'Run a department health check across my organization. I want to understand how each team is performing and where we need attention.',
    },
    {
      id: 'process_audit',
      icon: '⚙️',
      title: 'Audit Our Processes',
      description: 'Find bottlenecks and optimization opportunities',
      prompt: 'Help me audit our key business processes. I want to find bottlenecks, inefficiencies, and opportunities to streamline operations.',
    },
    {
      id: 'compliance_review',
      icon: '🛡️',
      title: 'Compliance Review',
      description: 'Make sure nothing is falling through the cracks',
      prompt: 'Run a compliance review for our business. I want to make sure we are meeting all regulatory requirements and nothing is falling through the cracks.',
    },
  ],
  enterprise: [
    {
      id: 'stakeholder_briefing',
      icon: '📋',
      title: 'Stakeholder Briefing',
      description: 'Prepare a strategic update for leadership',
      prompt: 'Help me prepare a stakeholder briefing. I need a strategic update covering our key initiatives, risks, and progress for the leadership team.',
    },
    {
      id: 'risk_assessment',
      icon: '⚠️',
      title: 'Risk Assessment',
      description: 'Identify and prioritize organizational risks',
      prompt: 'Run a comprehensive risk assessment for our organization. I want to identify, categorize, and prioritize the key risks we need to manage.',
    },
    {
      id: 'portfolio_review',
      icon: '📈',
      title: 'Portfolio Review',
      description: 'Evaluate your initiative portfolio health',
      prompt: 'Help me review our initiative portfolio. I want to evaluate which initiatives are on track, which need attention, and how resources are allocated.',
    },
  ],
};

export function FirstActionPicker({ persona, onSelect }: FirstActionPickerProps) {
  const actions = PERSONA_ACTIONS[persona] || PERSONA_ACTIONS.startup;

  return (
    <div className="max-w-lg mx-auto">
      <div className="grid gap-3">
        {actions.map((action, i) => (
          <button
            key={action.id}
            onClick={() => onSelect(action.id, action.prompt)}
            className="group flex items-start gap-4 p-4 bg-white border border-slate-200 rounded-xl hover:border-teal-300 hover:bg-teal-50/50 active:scale-[0.99] transition-all duration-200 shadow-sm hover:shadow-md text-left animate-[fadeInUp_0.3s_ease-out_both]"
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className="text-3xl flex-shrink-0 group-hover:scale-110 transition-transform duration-200">
              {action.icon}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-800 group-hover:text-teal-700 transition-colors">
                {action.title}
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                {action.description}
              </p>
            </div>
            <div className="ml-auto flex-shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity">
              <svg className="w-5 h-5 text-teal-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
