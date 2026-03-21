'use client';

import { QuestioningWizard } from '@/components/app-builder/QuestioningWizard';

export default function NewAppProjectPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Start a new app</h1>
      <p className="text-slate-500 mb-8">
        Answer a few questions to kick off your creative brief
      </p>
      <QuestioningWizard />
    </div>
  );
}
