import React from 'react';
import { Composition } from 'remotion';
import { LandingDemo, TOTAL_DURATION_FRAMES } from './LandingDemo';
import { VIDEO_FPS, VIDEO_WIDTH, VIDEO_HEIGHT } from './LandingDemo/constants';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LandingDemo"
    component={LandingDemo}
    durationInFrames={TOTAL_DURATION_FRAMES}
    fps={VIDEO_FPS}
    width={VIDEO_WIDTH}
    height={VIDEO_HEIGHT}
  />
);
