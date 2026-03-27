'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { PersonaType, PERSONA_INFO } from '@/services/onboarding';

interface DashboardPreviewProps {
  persona: PersonaType;
}

const DASHBOARD_SECTIONS: Record<PersonaType, { title: string; items: string[] }[]> = {
  solopreneur: [
    { title: 'This Week', items: ['Quick Tasks', 'Revenue Target'] },
    { title: 'Brain Dumps', items: ['Ideas', 'Action Items'] },
    { title: 'Content Queue', items: ['Drafts', 'Scheduled'] },
  ],
  startup: [
    { title: 'Growth Board', items: ['Experiments', 'Key Metrics'] },
    { title: 'Velocity', items: ['Active Workflows', 'Blockers'] },
    { title: 'Pipeline', items: ['Leads', 'Conversions'] },
  ],
  sme: [
    { title: 'Departments', items: ['Team Health', 'Open Items'] },
    { title: 'Compliance', items: ['Audits', 'Risk Register'] },
    { title: 'Reporting', items: ['KPIs', 'Monthly Report'] },
  ],
  enterprise: [
    { title: 'Approvals', items: ['Pending', 'Governance'] },
    { title: 'Executive View', items: ['Portfolio', 'Stakeholders'] },
    { title: 'Audit Trail', items: ['Actions', 'Compliance'] },
  ],
};

export function DashboardPreview({ persona }: DashboardPreviewProps) {
  const info = PERSONA_INFO[persona];
  const sections = DASHBOARD_SECTIONS[persona] || DASHBOARD_SECTIONS.startup;

  return (
    <div className="max-w-sm mx-auto">
      <div className="bg-slate-900 rounded-xl overflow-hidden shadow-2xl border border-slate-700/50 transform scale-90 origin-top">
        {/* Mini header */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-slate-700">
          <div className="flex gap-1">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <div className="w-2 h-2 rounded-full bg-yellow-400" />
            <div className="w-2 h-2 rounded-full bg-green-400" />
          </div>
          <div className="flex-1 text-center">
            <span className="text-[9px] text-slate-400 font-mono">pikar.ai/dashboard</span>
          </div>
        </div>

        {/* Mini dashboard content */}
        <div className="p-3">
          {/* KPI row */}
          <div className="grid grid-cols-3 gap-1.5 mb-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className={`bg-gradient-to-br ${info.color} rounded-lg p-2 opacity-80`}>
                <div className="w-6 h-1.5 bg-white/30 rounded-full mb-1" />
                <div className="w-10 h-2.5 bg-white/60 rounded-full" />
              </div>
            ))}
          </div>

          {/* Section cards */}
          <div className="grid grid-cols-3 gap-1.5">
            {sections.map((section, i) => (
              <div key={i} className="bg-slate-800 rounded-lg p-2">
                <div className="text-[8px] font-semibold text-slate-400 mb-1.5 truncate">
                  {section.title}
                </div>
                {section.items.map((item, j) => (
                  <div key={j} className="flex items-center gap-1 mb-1">
                    <div className="w-1 h-1 rounded-full bg-teal-400/50" />
                    <div className="text-[7px] text-slate-500 truncate">{item}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
