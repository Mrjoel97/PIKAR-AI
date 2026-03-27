'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { PersonaType, PERSONA_INFO } from '@/services/onboarding';

interface PersonaRevealCardProps {
  persona: PersonaType;
  onContinue: () => void;
}

const PERSONA_HIGHLIGHTS: Record<PersonaType, string[]> = {
  solopreneur: [
    'Lean, actionable advice — no corporate fluff',
    'Weekly priorities that you can actually execute solo',
    'Revenue-first thinking for every decision',
  ],
  startup: [
    'Growth experiments and rapid validation',
    'Burn rate awareness and runway planning',
    'Team alignment and velocity tracking',
  ],
  sme: [
    'Department coordination and process optimization',
    'Compliance monitoring and risk management',
    'Operational reporting and KPI tracking',
  ],
  enterprise: [
    'Stakeholder visibility and governance workflows',
    'Portfolio-level strategic planning',
    'Audit trails and approval orchestration',
  ],
};

export function PersonaRevealCard({ persona, onContinue }: PersonaRevealCardProps) {
  const info = PERSONA_INFO[persona];
  const highlights = PERSONA_HIGHLIGHTS[persona] || PERSONA_HIGHLIGHTS.startup;

  return (
    <div className="max-w-md mx-auto">
      <div
        className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${info.color} p-[2px] shadow-xl animate-[scaleIn_0.5s_ease-out_both]`}
      >
        <div className="bg-white rounded-[14px] p-6">
          {/* Icon and title */}
          <div className="text-center mb-4">
            <div className="text-5xl mb-3 animate-[bounceIn_0.6s_ease-out_0.3s_both]">
              {info.icon}
            </div>
            <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">
              Your Persona
            </div>
            <h3 className={`text-2xl font-bold bg-gradient-to-r ${info.color} bg-clip-text text-transparent`}>
              {info.title}
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              {info.description}
            </p>
          </div>

          {/* Highlights */}
          <div className="space-y-3 mb-6">
            {highlights.map((highlight, i) => (
              <div
                key={i}
                className="flex items-start gap-3 animate-[fadeInUp_0.3s_ease-out_both]"
                style={{ animationDelay: `${0.5 + i * 0.15}s` }}
              >
                <div className={`w-6 h-6 rounded-full bg-gradient-to-br ${info.color} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                  <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <span className="text-sm text-slate-700">{highlight}</span>
              </div>
            ))}
          </div>

          {/* Continue button */}
          <button
            onClick={onContinue}
            className={`w-full py-3 rounded-xl bg-gradient-to-r ${info.color} text-white font-semibold text-sm hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-lg animate-[fadeInUp_0.3s_ease-out_1s_both]`}
          >
            Looks great — let's continue!
          </button>
        </div>
      </div>
    </div>
  );
}
