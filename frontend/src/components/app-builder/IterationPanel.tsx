'use client';

import { useState } from 'react';

interface IterationPanelProps {
  onSubmit: (changeDescription: string) => void;
  isIterating: boolean;
}

/**
 * Inline panel for requesting screen edits via natural language.
 * Disabled when empty or while an iteration is in progress.
 */
export default function IterationPanel({ onSubmit, isIterating }: IterationPanelProps) {
  const [value, setValue] = useState('');

  const handleSubmit = () => {
    if (!value.trim() || isIterating) return;
    onSubmit(value.trim());
    setValue('');
  };

  const isDisabled = !value.trim() || isIterating;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">Request a change</h3>
      <textarea
        className="w-full resize-none rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
        rows={3}
        placeholder="Describe what you want to change..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isIterating}
      />
      <div className="mt-2 flex justify-end">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isDisabled}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
        >
          {isIterating ? 'Applying changes...' : 'Apply changes'}
        </button>
      </div>
    </div>
  );
}
