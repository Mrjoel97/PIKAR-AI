'use client';

import React, { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { WidgetProps } from './WidgetRegistry';
import { Copy, Check, Film, Code2 } from 'lucide-react';
import { GeneratedVideoComposition, GeneratedVideoInputProps } from './remotion/GeneratedVideoComposition';

const Player = dynamic(
  () => import('@remotion/player').then((m) => m.Player),
  { ssr: false }
);

export interface VideoSpecWidgetData {
  title?: string;
  prompt?: string;
  scenes?: Array<{ text: string; duration: number }>;
  fps?: number;
  durationInFrames?: number;
  remotion_code?: string;
  instructions?: string[];
  caption?: string;
}

export default function VideoSpecWidget({ definition }: WidgetProps) {
  const data = definition.data as VideoSpecWidgetData;
  const title = data?.title || 'Programmatic video';
  const prompt = data?.prompt;
  const scenes = data?.scenes ?? [];
  const fps = data?.fps ?? 30;
  const durationInFrames = data?.durationInFrames ?? 0;
  const remotionCode = data?.remotion_code;
  const instructions = data?.instructions || [];
  const caption = data?.caption;
  const [copied, setCopied] = useState(false);
  const [showCode, setShowCode] = useState(false);

  const canPlay = scenes.length > 0 && durationInFrames > 0;

  const playerInputProps = useMemo(
    () => ({ scenes, fps }),
    [scenes, fps]
  );

  const copyCode = () => {
    if (remotionCode) {
      navigator.clipboard.writeText(remotionCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200">
        <Film className="w-5 h-5 text-indigo-500" />
        <h3 className="font-semibold">{title}</h3>
      </div>

      {canPlay && (
        <div className="relative rounded-lg overflow-hidden bg-slate-900 aspect-video">
          <Player
            component={GeneratedVideoComposition as React.FC<unknown>}
            inputProps={playerInputProps}
            durationInFrames={durationInFrames}
            fps={fps}
            compositionWidth={1920}
            compositionHeight={1080}
            controls
            style={{ width: '100%', height: '100%' }}
            className="rounded-lg"
            acknowledgeRemotionLicense
          />
        </div>
      )}

      {caption && (
        <p className="text-sm text-slate-600 dark:text-slate-400">{caption}</p>
      )}

      {instructions.length > 0 && !showCode && (
        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">How to render to MP4</p>
          <ol className="list-decimal list-inside text-sm text-slate-700 dark:text-slate-300 space-y-1">
            {instructions.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {remotionCode && (
        <div>
          <button
            type="button"
            onClick={() => setShowCode((s) => !s)}
            className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400"
          >
            <Code2 className="w-4 h-4" />
            {showCode ? 'Hide' : 'Show'} Remotion code
          </button>
          {showCode && (
            <div className="relative mt-2">
              <pre className="p-3 rounded-lg bg-slate-900 text-slate-100 text-xs overflow-x-auto max-h-64 overflow-y-auto font-mono">
                {remotionCode}
              </pre>
              <button
                type="button"
                onClick={copyCode}
                className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy code'}
              </button>
            </div>
          )}
        </div>
      )}

      {!remotionCode && prompt && (
        <p className="text-sm text-slate-600 dark:text-slate-400">Prompt: {prompt}</p>
      )}
    </div>
  );
}
