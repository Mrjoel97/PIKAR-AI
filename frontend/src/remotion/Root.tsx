import React from 'react';
import { registerRoot, Composition } from 'remotion';
import { LandingDemo, TOTAL_DURATION_FRAMES } from './LandingDemo';
import { VIDEO_FPS, VIDEO_WIDTH, VIDEO_HEIGHT } from './LandingDemo/constants';

const RemotionRoot: React.FC = () => (
  <Composition
    id="LandingDemo"
    component={LandingDemo}
    durationInFrames={TOTAL_DURATION_FRAMES}
    fps={VIDEO_FPS}
    width={VIDEO_WIDTH}
    height={VIDEO_HEIGHT}
  />
);

registerRoot(RemotionRoot);
