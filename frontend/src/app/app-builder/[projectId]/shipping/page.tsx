'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { shipProject, advanceStage } from '@/services/app-builder';
import type { ShipTarget, ShipEvent } from '@/types/app-builder';

type TargetStatus = 'pending' | 'in-progress' | 'complete' | 'failed';

interface TargetConfig {
  id: ShipTarget;
  label: string;
  description: string;
  icon: string;
}

const TARGETS: TargetConfig[] = [
  { id: 'react',     label: 'React + TypeScript',  description: 'Modular components with Tailwind theme',         icon: '\u269b\ufe0f' },
  { id: 'pwa',       label: 'PWA',                 description: 'Installable web app for any device',             icon: '\ud83c\udf10' },
  { id: 'capacitor', label: 'iOS & Android',        description: 'Capacitor project for native app stores',        icon: '\ud83d\udcf1' },
  { id: 'video',     label: 'Walkthrough Video',    description: 'Remotion-rendered MP4 demo video',               icon: '\ud83c\udfac' },
];

/**
 * Shipping page — final GSD stage (FLOW-07).
 * Users select output targets (react, pwa, capacitor, video), trigger the ship process,
 * see real-time SSE progress per target, and download generated artifacts.
 */
export default function ShippingPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params?.projectId ?? '';
  const router = useRouter();

  const [selectedTargets, setSelectedTargets] = useState<Set<ShipTarget>>(
    new Set(['react', 'pwa', 'capacitor', 'video'] as ShipTarget[]),
  );
  const [targetStatus, setTargetStatus] = useState<Partial<Record<ShipTarget, TargetStatus>>>({});
  const [downloadUrls, setDownloadUrls] = useState<Partial<Record<ShipTarget, string>>>({});
  const [isShipping, setIsShipping] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleTarget = useCallback((target: ShipTarget) => {
    if (isShipping) return;
    setSelectedTargets((prev) => {
      const next = new Set(prev);
      if (next.has(target)) {
        next.delete(target);
      } else {
        next.add(target);
      }
      return next;
    });
  }, [isShipping]);

  const handleShip = useCallback(async () => {
    if (isShipping || selectedTargets.size === 0) return;
    setIsShipping(true);
    setError(null);

    // Initialise all selected targets to 'pending'
    const initialStatus: Partial<Record<ShipTarget, TargetStatus>> = {};
    for (const t of selectedTargets) {
      initialStatus[t] = 'pending';
    }
    setTargetStatus(initialStatus);

    // Local accumulators — avoid stale-state closure during streaming (established pattern)
    const accStatus: Partial<Record<ShipTarget, TargetStatus>> = { ...initialStatus };
    const accUrls: Partial<Record<ShipTarget, string>> = {};

    const onEvent = (event: ShipEvent) => {
      if (event.step === 'target_started' && event.target) {
        accStatus[event.target] = 'in-progress';
        setTargetStatus({ ...accStatus });
      } else if (event.step === 'target_complete' && event.target) {
        accStatus[event.target] = 'complete';
        if (event.url) {
          accUrls[event.target] = event.url;
          setDownloadUrls({ ...accUrls });
        }
        setTargetStatus({ ...accStatus });
      } else if (event.step === 'target_failed' && event.target) {
        accStatus[event.target] = 'failed';
        setTargetStatus({ ...accStatus });
      } else if (event.step === 'ship_complete') {
        if (event.downloads) {
          const merged = { ...accUrls, ...event.downloads } as Partial<Record<ShipTarget, string>>;
          setDownloadUrls(merged);
        }
        setIsDone(true);
        setIsShipping(false);
      }
    };

    try {
      await shipProject(projectId, Array.from(selectedTargets), onEvent);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ship process failed. Please try again.');
      setIsShipping(false);
    }
  }, [projectId, isShipping, selectedTargets]);

  const handleFinish = useCallback(async () => {
    try {
      await advanceStage(projectId, 'done');
    } catch {
      // Non-fatal — navigate regardless
    }
    router.push('/app-builder');
  }, [projectId, router]);

  const successCount = (Object.values(targetStatus) as TargetStatus[]).filter(
    (s) => s === 'complete',
  ).length;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-800 mb-1">Ship Your App</h1>
        <p className="text-sm text-slate-500">
          Select the output targets to generate. Each target will be built and packaged for
          download.
        </p>
      </div>

      {/* Target selection grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {TARGETS.map((target) => {
          const isSelected = selectedTargets.has(target.id);
          const status = targetStatus[target.id];

          return (
            <button
              key={target.id}
              type="button"
              onClick={() => toggleTarget(target.id)}
              disabled={isShipping}
              className={[
                'relative flex flex-col gap-2 rounded-xl border-2 p-4 text-left transition-all',
                isSelected && !isShipping
                  ? 'border-indigo-500 bg-indigo-50'
                  : isSelected && isShipping
                    ? 'border-indigo-400 bg-indigo-50 cursor-default'
                    : 'border-slate-200 bg-white hover:border-slate-300',
                !isSelected && 'opacity-60',
              ].join(' ')}
            >
              {/* Checkbox indicator */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl" aria-hidden="true">{target.icon}</span>
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{target.label}</p>
                    <p className="text-xs text-slate-500">{target.description}</p>
                  </div>
                </div>
                <StatusIndicator status={status} isSelected={isSelected} />
              </div>

              {/* Download button */}
              {status === 'complete' && downloadUrls[target.id] && (
                <a
                  href={downloadUrls[target.id]}
                  download
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1 inline-flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700 transition-colors self-start"
                >
                  Download
                </a>
              )}

              {/* Error message */}
              {status === 'failed' && (
                <p className="text-xs text-red-600 mt-1">Generation failed for this target.</p>
              )}
            </button>
          );
        })}
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Ship button */}
      {!isDone && (
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push(`/app-builder/${projectId}/verifying`)}
            disabled={isShipping}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Back
          </button>
          <button
            type="button"
            onClick={handleShip}
            disabled={isShipping || selectedTargets.size === 0}
            className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {isShipping ? 'Shipping...' : `Ship ${selectedTargets.size} Target${selectedTargets.size !== 1 ? 's' : ''}`}
          </button>
        </div>
      )}

      {/* Done state */}
      {isDone && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-green-200 bg-green-50 p-6 text-center">
          <p className="text-base font-semibold text-green-800">
            All Done! {successCount} target{successCount !== 1 ? 's' : ''} shipped successfully.
          </p>
          {successCount > 0 && (
            <p className="text-sm text-green-700">
              Your downloads are ready — click each target card to access them.
            </p>
          )}
          <button
            type="button"
            onClick={handleFinish}
            className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
          >
            Finish
          </button>
        </div>
      )}
    </div>
  );
}

/** Renders the per-target status indicator shown inside each target card. */
function StatusIndicator({
  status,
  isSelected,
}: {
  status: TargetStatus | undefined;
  isSelected: boolean;
}) {
  if (status === 'in-progress') {
    return (
      <span className="mt-0.5 h-4 w-4 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent shrink-0" />
    );
  }
  if (status === 'complete') {
    return (
      <span className="mt-0.5 shrink-0 text-green-600 text-base" aria-label="Complete">
        &#10003;
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="mt-0.5 shrink-0 text-red-500 text-base font-bold" aria-label="Failed">
        &#10005;
      </span>
    );
  }
  if (status === 'pending') {
    return (
      <span className="mt-0.5 h-3 w-3 rounded-full bg-indigo-300 shrink-0" aria-label="Pending" />
    );
  }
  // Not yet started — show checkbox-style indicator
  return (
    <span
      className={[
        'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border-2',
        isSelected ? 'border-indigo-500 bg-indigo-500' : 'border-slate-300 bg-white',
      ].join(' ')}
      aria-hidden="true"
    >
      {isSelected && (
        <svg viewBox="0 0 10 8" className="h-2.5 w-2.5 fill-white">
          <path d="M1 4l3 3 5-6" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </span>
  );
}
