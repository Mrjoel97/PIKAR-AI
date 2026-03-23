'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import VariantComparisonGrid from '@/components/app-builder/VariantComparisonGrid';
import DevicePreviewFrame from '@/components/app-builder/DevicePreviewFrame';
import GenerationProgress from '@/components/app-builder/GenerationProgress';
import IterationPanel from '@/components/app-builder/IterationPanel';
import ApprovalCheckpointCard from '@/components/app-builder/ApprovalCheckpointCard';
import VersionHistoryPanel from '@/components/app-builder/VersionHistoryPanel';
import {
  getProject,
  generateScreen,
  generateDeviceVariant,
  selectVariant,
  iterateScreen,
  getScreenHistory,
  rollbackVariant,
  approveScreen,
} from '@/services/app-builder';
import type {
  AppProject,
  ScreenVariant,
  DeviceType,
  GenerationEvent,
  IterationEvent,
  BuildPlanPhase,
} from '@/types/app-builder';

interface ScreenEntry {
  name: string;
  page: string;
  device: string;
}

/**
 * Building page — displays build plan sidebar, triggers screen generation,
 * shows variant comparison grid and live device preview.
 * Integrates iteration panel, version history, and approval checkpoint
 * to complete the generate-preview-iterate-approve loop (FLOW-05).
 */
export default function BuildingPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params?.projectId ?? '';

  const [project, setProject] = useState<AppProject | null>(null);
  const [variants, setVariants] = useState<ScreenVariant[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingDevice, setIsGeneratingDevice] = useState(false);
  const [currentDevice, setCurrentDevice] = useState<DeviceType>('DESKTOP');
  const [generationStep, setGenerationStep] = useState('');
  const [variantsGenerated, setVariantsGenerated] = useState(0);
  const [activeScreenId, setActiveScreenId] = useState<string | null>(null);

  // Iteration state
  const [isIterating, setIsIterating] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [versionHistory, setVersionHistory] = useState<ScreenVariant[]>([]);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId).then(setProject).catch(console.error);
  }, [projectId]);

  const loadVersionHistory = useCallback(async () => {
    if (!activeScreenId) return;
    try {
      const history = await getScreenHistory(projectId, activeScreenId);
      setVersionHistory(history);
    } catch {
      // Non-fatal — history unavailable
    }
  }, [projectId, activeScreenId]);

  // Load version history and reset approval when the active screen changes
  useEffect(() => {
    if (!activeScreenId) return;
    setIsApproved(false);
    void loadVersionHistory();
  }, [activeScreenId, loadVersionHistory]);

  const handleGenerateScreen = useCallback(
    async (screen: ScreenEntry) => {
      if (isGenerating) return;
      setIsGenerating(true);
      setVariants([]);
      setSelectedVariantId(null);
      setVariantsGenerated(0);
      setGenerationStep('Starting generation...');
      setActiveScreenId(null);
      // Reset iteration state for the new screen
      setIsApproved(false);
      setVersionHistory([]);

      const accumulated: ScreenVariant[] = [];

      const onEvent = (event: GenerationEvent) => {
        if (event.step === 'generating') {
          setGenerationStep(event.message ?? 'Generating...');
        } else if (event.step === 'variant_generated') {
          const v: ScreenVariant = {
            id: event.variant_id ?? `var-${event.variant_index ?? accumulated.length}`,
            screen_id: event.screen_id ?? '',
            variant_index: event.variant_index ?? accumulated.length,
            screenshot_url: event.screenshot_url ?? null,
            html_url: event.html_url ?? null,
            is_selected: accumulated.length === 0,
            prompt_used: null,
            created_at: new Date().toISOString(),
          };
          accumulated.push(v);
          setVariants([...accumulated]);
          setVariantsGenerated(accumulated.length);
          if (event.screen_id) setActiveScreenId(event.screen_id);
        } else if (event.step === 'ready') {
          const finalVariants = event.variants ?? accumulated;
          setVariants(finalVariants);
          setIsGenerating(false);
          const first = finalVariants[0];
          if (first) {
            setSelectedVariantId(first.id);
            if (first.screen_id) setActiveScreenId(first.screen_id);
          }
        } else if (event.step === 'error') {
          setIsGenerating(false);
          setGenerationStep('Generation failed. Please try again.');
        }
      };

      try {
        await generateScreen(projectId, screen.name, screen.page, onEvent);
      } catch {
        setIsGenerating(false);
        setGenerationStep('Generation failed. Please try again.');
      }
    },
    [projectId, isGenerating],
  );

  const handleVariantSelect = useCallback(
    async (variantId: string) => {
      setSelectedVariantId(variantId);
      if (activeScreenId) {
        try {
          await selectVariant(projectId, activeScreenId, variantId);
        } catch {
          // Selection failed — keep local state
        }
      }
    },
    [projectId, activeScreenId],
  );

  const handleDeviceChange = useCallback(
    async (device: DeviceType) => {
      setCurrentDevice(device);
      if (device === 'DESKTOP') return;

      // Check if a device variant already exists
      const existingDeviceVariant = variants.find((v) => v.device_type === device);
      if (existingDeviceVariant) {
        setSelectedVariantId(existingDeviceVariant.id);
        return;
      }

      // Generate on-demand device variant
      if (!activeScreenId) return;
      const selectedVariant = variants.find((v) => v.id === selectedVariantId);
      const promptUsed = selectedVariant?.prompt_used ?? '';

      setIsGeneratingDevice(true);
      const onEvent = (event: GenerationEvent) => {
        if (event.step === 'device_generated') {
          const v: ScreenVariant = {
            id: event.variant_id ?? `var-device-${device}`,
            screen_id: activeScreenId,
            variant_index: variants.length,
            screenshot_url: event.screenshot_url ?? null,
            html_url: event.html_url ?? null,
            is_selected: false,
            prompt_used: promptUsed,
            device_type: device,
            created_at: new Date().toISOString(),
          };
          setVariants((prev) => [...prev, v]);
          setSelectedVariantId(v.id);
        } else if (event.step === 'ready') {
          setIsGeneratingDevice(false);
        }
      };

      try {
        await generateDeviceVariant(projectId, activeScreenId, device, promptUsed, onEvent);
      } catch {
        setIsGeneratingDevice(false);
      }
    },
    [projectId, activeScreenId, variants, selectedVariantId],
  );

  const handleIterate = useCallback(
    async (changeDescription: string) => {
      if (!activeScreenId || isIterating) return;
      setIsIterating(true);

      // Local accumulator to avoid stale-state closure (same pattern as handleGenerateScreen)
      let newVariant: ScreenVariant | null = null;

      const onEvent = (event: IterationEvent) => {
        if (event.step === 'edit_complete') {
          newVariant = {
            id: event.variant_id ?? `iter-${Date.now()}`,
            screen_id: event.screen_id ?? activeScreenId,
            variant_index: 0,
            screenshot_url: event.screenshot_url ?? null,
            html_url: event.html_url ?? null,
            is_selected: true,
            prompt_used: changeDescription,
            iteration: event.iteration,
            created_at: new Date().toISOString(),
          };
          // Prepend the new iteration, deselect previous variants
          setVariants((prev) => [
            newVariant!,
            ...prev.map((v) => ({ ...v, is_selected: false })),
          ]);
          setSelectedVariantId(newVariant.id);
        } else if (event.step === 'ready') {
          setIsIterating(false);
          void loadVersionHistory();
        } else if (event.step === 'error') {
          setIsIterating(false);
        }
      };

      try {
        await iterateScreen(projectId, activeScreenId, changeDescription, onEvent);
      } catch {
        setIsIterating(false);
      }
    },
    [projectId, activeScreenId, isIterating, loadVersionHistory],
  );

  const handleApprove = useCallback(async () => {
    if (!activeScreenId) return;
    await approveScreen(projectId, activeScreenId);
    setIsApproved(true);
    // Note: does NOT call advanceStage — stage advancement is a separate user action
  }, [projectId, activeScreenId]);

  const handleRollback = useCallback(
    async (variantId: string) => {
      if (!activeScreenId) return;
      try {
        await rollbackVariant(projectId, activeScreenId, variantId);
        // Update local variants selection
        setVariants((prev) =>
          prev.map((v) => ({ ...v, is_selected: v.id === variantId })),
        );
        setSelectedVariantId(variantId);
        void loadVersionHistory();
      } catch {
        // Rollback failed — keep local state
      }
    },
    [projectId, activeScreenId, loadVersionHistory],
  );

  const selectedVariant = variants.find((v) => v.id === selectedVariantId) ?? null;
  const previewUrl =
    currentDevice === 'DESKTOP'
      ? (selectedVariant?.html_url ?? null)
      : (variants.find((v) => v.device_type === currentDevice)?.html_url ??
        selectedVariant?.html_url ??
        null);

  const buildPlan: BuildPlanPhase[] = project?.build_plan ?? [];

  return (
    <div className="flex flex-col gap-6 md:flex-row">
      {/* Build plan sidebar */}
      <aside className="w-full shrink-0 md:w-[280px]">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Build Plan
        </h2>
        {buildPlan.length === 0 && (
          <p className="text-sm text-slate-400">Loading build plan...</p>
        )}
        {buildPlan.map((phase) => (
          <div key={phase.phase} className="mb-4">
            <p className="mb-2 text-xs font-semibold text-slate-600">
              Phase {phase.phase}: {phase.label}
            </p>
            <ul className="space-y-1">
              {phase.screens.map((screen) => (
                <li key={`${phase.phase}-${screen.page}`}>
                  <button
                    type="button"
                    onClick={() => handleGenerateScreen(screen)}
                    disabled={isGenerating}
                    className="w-full rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                  >
                    {screen.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </aside>

      {/* Main content */}
      <main className="flex-1 space-y-6">
        {isGenerating && (
          <GenerationProgress
            currentStep={generationStep}
            variantsGenerated={variantsGenerated}
            totalVariants={3}
          />
        )}

        {variants.length > 0 && !isGenerating && (
          <>
            <div>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">Choose a variant</h2>
              <VariantComparisonGrid
                variants={variants}
                selectedId={selectedVariantId}
                onSelect={handleVariantSelect}
              />
            </div>

            <div>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">Live preview</h2>
              <DevicePreviewFrame
                htmlUrl={previewUrl}
                device={currentDevice}
                onDeviceChange={handleDeviceChange}
                isGeneratingDevice={isGeneratingDevice}
              />
            </div>

            <IterationPanel onSubmit={handleIterate} isIterating={isIterating} />

            {versionHistory.length > 0 && (
              <VersionHistoryPanel variants={versionHistory} onRollback={handleRollback} />
            )}

            <ApprovalCheckpointCard
              screenName={project?.title ?? 'Screen'}
              onApprove={handleApprove}
              isApproved={isApproved}
            />
          </>
        )}

        {!isGenerating && variants.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 py-16 text-center">
            <p className="text-slate-400">
              Select a screen from the build plan to start generating
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
