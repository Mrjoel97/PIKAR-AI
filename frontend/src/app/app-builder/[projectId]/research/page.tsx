'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { Search, Sparkles, Save } from 'lucide-react';
import { startResearch, approveBrief, advanceStage, resumeAutopilot } from '@/services/app-builder';
import { DesignBriefCard } from '@/components/app-builder/DesignBriefCard';
import { SitemapCard } from '@/components/app-builder/SitemapCard';
import { BuildPlanView } from '@/components/app-builder/BuildPlanView';
import type { DesignBrief, SitemapPage, BuildPlanPhase, ResearchEvent } from '@/types/app-builder';

type ResearchStep = ResearchEvent['step'] | 'idle';

const STEP_META: Record<string, { icon: React.ElementType; label: string }> = {
  idle:         { icon: Search,    label: 'Starting research...' },
  searching:    { icon: Search,    label: 'Researching' },
  synthesizing: { icon: Sparkles,  label: 'Synthesizing' },
  saving:       { icon: Save,      label: 'Saving' },
};

export default function ResearchPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const projectId = params.projectId;

  const [researchStep, setResearchStep] = useState<ResearchStep>('idle');
  const [stepMessage, setStepMessage] = useState<string>('');
  const [brief, setBrief] = useState<DesignBrief | null>(null);
  const [sitemap, setSitemap] = useState<SitemapPage[]>([]);
  const [buildPlan, setBuildPlan] = useState<BuildPlanPhase[] | null>(null);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function run() {
      try {
        // Ensure stage is 'research' (idempotent)
        await advanceStage(projectId, 'research');
      } catch {
        // Non-fatal — stage may already be set or endpoint unavailable in tests
      }

      startResearch(projectId, (event: ResearchEvent) => {
        setResearchStep(event.step);
        setStepMessage(event.message ?? '');

        if (event.step === 'ready' && event.data) {
          const { colors, typography, spacing, raw_markdown, sitemap: sitemapData } = event.data;
          setBrief({
            colors: colors ?? [],
            typography: typography ?? { heading: '', body: '' },
            spacing: spacing ?? { base_unit: '4px' },
            raw_markdown: raw_markdown ?? '',
          });
          setSitemap(sitemapData ?? []);
        }

        if (event.step === 'error') {
          setError(event.message ?? 'Research failed');
        }
      }).catch((err: Error) => {
        if (err.name !== 'AbortError') setError(err.message);
      });
    }

    void run();
    return () => controller.abort();
  }, [projectId]);

  async function handleApprove() {
    if (!brief || isApproving) return;
    setIsApproving(true);
    try {
      const result = await approveBrief(projectId, {
        design_system: {
          colors: brief.colors,
          typography: brief.typography,
          spacing: brief.spacing,
        },
        sitemap,
        raw_markdown: brief.raw_markdown,
      });
      setBuildPlan(result.build_plan);
      // If autopilot is active and parked at paused_brief, this kicks it
      // into the after_brief transition. 409 means autopilot isn't running
      // for this project — that's fine, manual flow continues as before.
      try {
        await resumeAutopilot(projectId, {});
      } catch {
        // Not in autopilot mode; ignore.
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Approval failed');
    } finally {
      setIsApproving(false);
    }
  }

  const isResearching = researchStep !== 'ready' && researchStep !== 'error';
  const meta = STEP_META[researchStep] ?? STEP_META.idle;
  const StepIcon = meta.icon;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Design Research</h1>
        <p className="text-slate-500 text-sm">
          AI is generating your design system and sitemap. Review and approve before building.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Progress indicator — shown while research is active */}
      <AnimatePresence mode="wait">
        {isResearching && (
          <motion.div
            key={researchStep}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="flex flex-col items-center justify-center py-16 gap-4"
          >
            <div className="flex items-center gap-3 text-indigo-600">
              <StepIcon className="w-6 h-6 animate-pulse" />
              <span className="text-lg font-semibold">{meta.label}</span>
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            </div>
            {stepMessage && (
              <p className="text-sm text-slate-500 max-w-sm text-center">{stepMessage}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Editable cards — shown after research completes */}
      {researchStep === 'ready' && brief && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DesignBriefCard brief={brief} onChange={setBrief} />
            <SitemapCard sitemap={sitemap} onChange={setSitemap} />
          </div>

          {/* Approve button */}
          <div className="flex justify-center">
            <button
              type="button"
              onClick={() => void handleApprove()}
              disabled={isApproving}
              className="px-8 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isApproving ? 'Generating Build Plan...' : 'Approve & Generate Build Plan'}
            </button>
          </div>

          {/* Build plan — shown after approval */}
          {buildPlan && (
            <div className="space-y-4">
              <BuildPlanView buildPlan={buildPlan} />
              <div className="flex justify-center">
                <button
                  type="button"
                  onClick={() => router.push(`/app-builder/${projectId}/building`)}
                  className="px-8 py-3 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 transition-colors"
                >
                  Continue to Building
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Approve button shown but disabled during research (for test access) */}
      {isResearching && (
        <div className="flex justify-center">
          <button
            type="button"
            disabled
            aria-label="Approve & Generate Build Plan"
            className="px-8 py-3 bg-indigo-600 text-white font-semibold rounded-xl opacity-40 cursor-not-allowed"
          >
            Approve & Generate Build Plan
          </button>
        </div>
      )}
    </div>
  );
}
