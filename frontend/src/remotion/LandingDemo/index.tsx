// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import {
  AbsoluteFill,
  Audio,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import {
  VIDEO_FPS,
  INTRO_DURATION,
  BRIEFING_DURATION,
  WORKFLOW_DURATION,
  CONTENT_DURATION,
  RESEARCH_DURATION,
  ORCHESTRATION_DURATION,
  DASHBOARD_DURATION,
  OUTRO_DURATION,
  TRANSITION_FRAMES,
} from './constants';
import { IntroScene } from './scenes/IntroScene';
import { BriefingScene } from './scenes/BriefingScene';
import { WorkflowScene } from './scenes/WorkflowScene';
import { ContentScene } from './scenes/ContentScene';
import { ResearchScene } from './scenes/ResearchScene';
import { OrchestrationScene } from './scenes/OrchestrationScene';
import { DashboardScene } from './scenes/DashboardScene';
import { OutroScene } from './scenes/OutroScene';

export { TOTAL_DURATION_FRAMES } from './duration';

/**
 * Scene definitions in playback order.
 * Each entry maps a React component to its duration in seconds.
 */
const SCENES: { component: React.FC; durationSec: number }[] = [
  { component: IntroScene, durationSec: INTRO_DURATION },
  { component: BriefingScene, durationSec: BRIEFING_DURATION },
  { component: WorkflowScene, durationSec: WORKFLOW_DURATION },
  { component: ContentScene, durationSec: CONTENT_DURATION },
  { component: ResearchScene, durationSec: RESEARCH_DURATION },
  { component: OrchestrationScene, durationSec: ORCHESTRATION_DURATION },
  { component: DashboardScene, durationSec: DASHBOARD_DURATION },
  { component: OutroScene, durationSec: OUTRO_DURATION },
];

const BackgroundMusic: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Volume: fade in first 2s, 30% during body, fade out last 2s
  const volume = interpolate(
    frame,
    [0, fps * 2, durationInFrames - fps * 2, durationInFrames],
    [0, 0.3, 0.3, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  try {
    return <Audio src={staticFile('audio/bg-ambient.mp3')} volume={volume} />;
  } catch {
    return null;
  }
};

export const LandingDemo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#f8fafa' }}>
      <BackgroundMusic />
      <TransitionSeries>
        {SCENES.map((scene, i) => {
          const Scene = scene.component;
          return (
            <React.Fragment key={i}>
              {/* Fade transition between scenes (skip before the first) */}
              {i > 0 && (
                <TransitionSeries.Transition
                  presentation={fade()}
                  timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
                />
              )}
              <TransitionSeries.Sequence
                durationInFrames={scene.durationSec * VIDEO_FPS}
              >
                <Scene />
              </TransitionSeries.Sequence>
            </React.Fragment>
          );
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
