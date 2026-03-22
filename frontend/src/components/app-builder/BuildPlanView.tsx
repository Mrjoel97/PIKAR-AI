'use client';

import type { BuildPlanPhase } from '@/types/app-builder';

interface BuildPlanViewProps {
  buildPlan: BuildPlanPhase[];
}

export function BuildPlanView({ buildPlan }: BuildPlanViewProps) {
  return (
    <div
      data-testid="build-plan-view"
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm"
    >
      <h3 className="text-sm font-semibold text-slate-700 mb-4">Build Plan</h3>

      {buildPlan.length === 0 ? (
        <p className="text-sm text-slate-400">No phases generated yet.</p>
      ) : (
        <div className="space-y-4">
          {buildPlan.map((phase) => (
            <div key={phase.phase} className="border border-slate-100 rounded-lg p-4">
              {/* Phase header */}
              <div className="flex items-center gap-3 mb-3">
                <span className="flex items-center justify-center w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold shrink-0">
                  {phase.phase}
                </span>
                <span className="font-medium text-slate-800 text-sm">
                  Phase {phase.phase}: {phase.label}
                </span>
              </div>

              {/* Screens */}
              {phase.screens.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {phase.screens.map((screen, i) => (
                    <span
                      key={i}
                      className="bg-indigo-50 text-indigo-700 px-2 py-1 rounded text-xs"
                    >
                      {screen.name}
                    </span>
                  ))}
                </div>
              )}

              {/* Dependencies */}
              <p className="text-xs text-slate-400">
                {phase.dependencies.length > 0
                  ? `Depends on: Phase ${phase.dependencies.join(', Phase ')}`
                  : 'No dependencies'}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
