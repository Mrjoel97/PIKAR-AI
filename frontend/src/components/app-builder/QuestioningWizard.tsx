'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { QUESTIONS } from '@/types/app-builder';
import { QuestionStep } from './QuestionStep';
import { createProject } from '@/services/app-builder';

/**
 * Multi-step creative questioning wizard.
 *
 * Steps 0-3: choice cards that auto-advance on selection.
 * Step 4 (name): free-text input + "Start Building" submit button.
 * On submit, calls POST /app-builder/projects and navigates to /app-builder/{id}.
 */
export function QuestioningWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentQuestion = QUESTIONS[step];
  const isFinalStep = step === QUESTIONS.length - 1; // step 4 — "name"
  const isNameStep = currentQuestion.id === 'name';

  function handleSelect(questionId: string, value: string) {
    const updated = { ...answers, [questionId]: value };
    setAnswers(updated);

    // Auto-advance for all choice steps except the last one
    if (!isFinalStep) {
      setStep((prev) => prev + 1);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!answers.name?.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      const project = await createProject({
        title: answers.name.trim(),
        creative_brief: answers,
      });
      router.push(`/app-builder/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Step progress indicator */}
      <p className="text-xs text-slate-400 font-medium mb-4 text-center">
        Step {step + 1} of {QUESTIONS.length}
      </p>

      {/* Back button */}
      {step > 0 && (
        <button
          type="button"
          onClick={() => setStep((prev) => prev - 1)}
          className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4"
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>
      )}

      {/* Animated step content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {/* Question prompt */}
          <h2 className="text-xl font-semibold text-slate-900 mb-6 text-center">
            {currentQuestion.prompt}
          </h2>

          {/* Choice cards (steps 0-3) */}
          {!isNameStep && (
            <QuestionStep
              question={currentQuestion}
              selectedValue={answers[currentQuestion.id]}
              onSelect={handleSelect}
            />
          )}

          {/* Free-text name input (step 4) */}
          {isNameStep && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <input
                type="text"
                placeholder="e.g. My Startup Landing Page"
                value={answers.name ?? ''}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, name: e.target.value }))
                }
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                autoFocus
              />

              {error && (
                <p className="text-sm text-red-500">{error}</p>
              )}

              <button
                type="submit"
                disabled={submitting || !answers.name?.trim()}
                className="w-full rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Starting…' : 'Start Building'}
              </button>
            </form>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
