/**
 * Remotion root for server-side render. One composition: GeneratedVideo.
 * Render with: npx remotion render src/Root.tsx GeneratedVideo out.mp4 --props=props.json
 * Props JSON: { "scenes": [{ "text": "...", "duration": 5 }], "fps": 30, "durationInFrames": 150 }
 */
import React from 'react';
import { Composition } from 'remotion';
import { GeneratedVideoComposition, GeneratedVideoInputProps } from './Composition';

import { SceneInput } from './Composition';

const defaultProps = {
  scenes: [] as SceneInput[],
  fps: 30,
  durationInFrames: 150,
  bgMusicUrl: undefined as string | undefined, // Explicit null/undefined type
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="GeneratedVideo"
      component={GeneratedVideoComposition as any}
      durationInFrames={defaultProps.durationInFrames}
      fps={defaultProps.fps}
      width={1920}
      height={1080}
      defaultProps={defaultProps as any}
      calculateMetadata={({ props }) => {
        const p = props as any as GeneratedVideoInputProps;
        const fps = p.fps ?? 30;
        const scenesDurationFrames = (p.scenes || []).reduce((total, scene) => {
          const durationSeconds = Math.max(0, Number(scene.duration) || 0);
          return total + Math.round(durationSeconds * fps);
        }, 0);
        const selectedDuration = p.durationInFrames ?? scenesDurationFrames;
        const computedDuration = Math.max(
          1,
          selectedDuration || defaultProps.durationInFrames
        );
        return {
          durationInFrames: computedDuration,
        };
      }}
    />
  </>
);
