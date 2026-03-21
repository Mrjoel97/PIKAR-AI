'use client';

import { Check, HelpCircle, Search, FileText, Hammer, CheckCircle, Rocket, Star } from 'lucide-react';
import { GSD_STAGES, type GsdStage } from '@/types/app-builder';

const ICON_MAP: Record<string, React.ElementType> = {
  HelpCircle,
  Search,
  FileText,
  Hammer,
  CheckCircle,
  Rocket,
  Star,
};

interface GsdProgressBarProps {
  currentStage: GsdStage;
}

export function GsdProgressBar({ currentStage }: GsdProgressBarProps) {
  const currentIndex = GSD_STAGES.findIndex((s) => s.id === currentStage);

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 py-3">
      <ol className="flex items-center gap-1 sm:gap-2" role="list">
        {GSD_STAGES.map((stage, index) => {
          const completed = index < currentIndex;
          const current = index === currentIndex;
          const StageIcon = ICON_MAP[stage.icon] ?? HelpCircle;

          return (
            <li
              key={stage.id}
              className="flex flex-col items-center flex-1 min-w-0"
              aria-current={current ? 'step' : undefined}
            >
              {/* Icon circle */}
              <div
                className={[
                  'flex items-center justify-center w-7 h-7 rounded-full mb-1 shrink-0',
                  completed
                    ? 'bg-green-500 text-white'
                    : current
                    ? 'bg-indigo-600 text-white ring-2 ring-indigo-300'
                    : 'bg-slate-200 text-slate-400',
                ].join(' ')}
              >
                {completed ? (
                  <Check className="w-4 h-4" aria-label={`${stage.label} complete`} />
                ) : (
                  <StageIcon className="w-4 h-4" aria-hidden />
                )}
              </div>

              {/* Label */}
              <span
                className={[
                  'text-[10px] sm:text-xs font-medium truncate w-full text-center',
                  completed
                    ? 'text-green-600'
                    : current
                    ? 'text-indigo-600'
                    : 'text-slate-400',
                ].join(' ')}
              >
                {stage.label}
              </span>
            </li>
          );
        })}
      </ol>

      {/* Stage banner */}
      <p className="mt-1 text-center text-[10px] font-semibold tracking-widest text-indigo-500 uppercase">
        Stage {currentIndex + 1} of {GSD_STAGES.length} &mdash;{' '}
        {GSD_STAGES[currentIndex]?.label}
      </p>
    </div>
  );
}
