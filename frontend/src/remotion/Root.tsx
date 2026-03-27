// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { Composition } from 'remotion';
import { LandingDemo, TOTAL_DURATION_FRAMES } from './LandingDemo';
import { VIDEO_FPS, VIDEO_WIDTH, VIDEO_HEIGHT } from './LandingDemo/constants';
import {
  OAuthDemo,
  TOTAL_DURATION_FRAMES as OAUTH_TOTAL_FRAMES,
} from './OAuthDemo';
import {
  VIDEO_FPS as OAUTH_FPS,
  VIDEO_WIDTH as OAUTH_WIDTH,
  VIDEO_HEIGHT as OAUTH_HEIGHT,
} from './OAuthDemo/constants';

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="LandingDemo"
      component={LandingDemo}
      durationInFrames={TOTAL_DURATION_FRAMES}
      fps={VIDEO_FPS}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
    />
    <Composition
      id="OAuthDemo"
      component={OAuthDemo}
      durationInFrames={OAUTH_TOTAL_FRAMES}
      fps={OAUTH_FPS}
      width={OAUTH_WIDTH}
      height={OAUTH_HEIGHT}
    />
  </>
);
