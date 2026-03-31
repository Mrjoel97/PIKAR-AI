'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState } from 'react';
import { PersonaType, TONE_OPTIONS, VERBOSITY_OPTIONS } from '@/services/onboarding';

interface PreferencesInlineFormProps {
  persona: PersonaType | null;
  onSubmit: (prefs: { tone: string; verbosity: string }) => void;
}

const PERSONA_DEFAULTS: Record<string, { tone: string; verbosity: string }> = {
  solopreneur: { tone: 'casual', verbosity: 'concise' },
  startup: { tone: 'enthusiastic', verbosity: 'balanced' },
  sme: { tone: 'professional', verbosity: 'detailed' },
  enterprise: { tone: 'professional', verbosity: 'detailed' },
};

export function PreferencesInlineForm({ persona, onSubmit }: PreferencesInlineFormProps) {
  const defaults = persona ? PERSONA_DEFAULTS[persona] || PERSONA_DEFAULTS.startup : PERSONA_DEFAULTS.startup;

  const [tone, setTone] = useState(defaults.tone);
  const [verbosity, setVerbosity] = useState(defaults.verbosity);

  const handleSubmit = () => {
    onSubmit({ tone, verbosity });
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        {/* Tone selection */}
        <div className="mb-5">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Communication Tone
          </label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {TONE_OPTIONS.map((option) => (
              <button
                key={option.id}
                onClick={() => setTone(option.id)}
                className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border-2 transition-all duration-200 ${
                  tone === option.id
                    ? 'border-teal-500 bg-teal-50 text-teal-700 shadow-sm'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <span className="text-xl">{option.icon}</span>
                <span className="text-xs font-semibold">{option.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Verbosity selection */}
        <div className="mb-6">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Detail Level
          </label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {VERBOSITY_OPTIONS.map((option) => (
              <button
                key={option.id}
                onClick={() => setVerbosity(option.id)}
                className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border-2 transition-all duration-200 ${
                  verbosity === option.id
                    ? 'border-teal-500 bg-teal-50 text-teal-700 shadow-sm'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <span className="text-xl">{option.icon}</span>
                <span className="text-xs font-semibold">{option.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Confirm */}
        <button
          onClick={handleSubmit}
          className="w-full py-3 rounded-xl bg-teal-600 text-white font-semibold text-sm hover:bg-teal-700 active:scale-[0.98] transition-all duration-200 shadow-sm"
        >
          That's perfect — let's go!
        </button>
      </div>
    </div>
  );
}
