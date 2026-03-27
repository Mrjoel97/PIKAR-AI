'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import type { Question } from '@/types/app-builder';

interface QuestionStepProps {
  question: Question;
  selectedValue?: string;
  onSelect: (questionId: string, value: string) => void;
}

/**
 * Renders choice cards for a single question step.
 * When question.choices is empty (the name step) this component renders nothing —
 * QuestioningWizard handles the free-text input directly.
 */
export function QuestionStep({ question, selectedValue, onSelect }: QuestionStepProps) {
  if (question.choices.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 w-full">
      {question.choices.map((choice) => {
        const isSelected = choice === selectedValue;
        return (
          <button
            key={choice}
            type="button"
            onClick={() => onSelect(question.id, choice)}
            className={[
              'rounded-xl px-4 py-5 text-sm font-medium text-left transition-colors',
              isSelected
                ? 'border-2 border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:bg-slate-50',
            ].join(' ')}
          >
            {choice}
          </button>
        );
      })}
    </div>
  );
}
