// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, Building2 } from 'lucide-react';
import { PERSONA_SHELL_CONFIG } from './personaShellConfig';

const config = PERSONA_SHELL_CONFIG['sme'];

export function SmeShell({ children }: { children?: React.ReactNode }) {
  return (
    <div className={`min-h-screen ${config.bgColor}`}>
      {/* Persona Header */}
      <header className="relative overflow-hidden" role="banner">
        <div
          className={`bg-gradient-to-r ${config.gradient} px-4 sm:px-6 lg:px-8 py-6`}
        >
          {/* Decorative blur circle */}
          <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
          <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg">
                <Building2 className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">
                  {config.label} Workspace
                </h1>
                <p className="text-sm text-white/80 mt-0.5">
                  {config.tagline}
                </p>
              </div>
            </div>
            {/* Quick Actions Row */}
            <nav className="flex flex-wrap gap-2" aria-label="Quick actions">
              {config.quickActions.map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/15 hover:bg-white/25 backdrop-blur-sm text-white text-xs font-medium transition-colors"
                >
                  {action.label}
                  <ArrowRight size={12} />
                </Link>
              ))}
            </nav>
          </div>
          {/* KPI preview labels */}
          <div className="relative mt-4 flex flex-wrap gap-3">
            {config.kpiLabels.map((kpi) => (
              <span
                key={kpi}
                className="inline-flex items-center px-2.5 py-1 rounded-full bg-white/10 text-white/90 text-[11px] font-medium tracking-wide"
              >
                {kpi}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-4 sm:p-6">{children}</main>
    </div>
  );
}
