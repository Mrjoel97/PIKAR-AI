import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import {
  VIDEO_FPS,
  INTRO_DURATION,
  APP_IDENTITY_DURATION,
  CONSENT_SCREEN_DURATION,
  GMAIL_READONLY_DURATION,
  GMAIL_MODIFY_DURATION,
  GMAIL_SEND_DURATION,
  CALENDAR_DURATION,
  YOUTUBE_CONNECTION_DURATION,
  SECURITY_DURATION,
  OUTRO_DURATION,
  TRANSITION_FRAMES,
  TOTAL_DURATION_FRAMES,
} from './constants';
import { IntroScene } from './scenes/IntroScene';
import { AppIdentityScene } from './scenes/AppIdentityScene';
import { ConsentScreenScene } from './scenes/ConsentScreenScene';
import {
  GmailReadonlyScene,
  GmailModifyScene,
  GmailSendScene,
  CalendarScene,
} from './scenes/ScopeDemoScene';
import { YouTubeConnectionScene } from './scenes/YouTubeConnectionScene';
import { SecurityScene } from './scenes/SecurityScene';
import { OutroScene } from './scenes/OutroScene';

export { TOTAL_DURATION_FRAMES };

/**
 * Cross-dissolve wrapper: fades in at start, fades out at end
 */
const SceneWithTransition: React.FC<{
  children: React.ReactNode;
  durationFrames: number;
}> = ({ children, durationFrames }) => {
  const frame = useCurrentFrame();

  const fadeIn = interpolate(frame, [0, TRANSITION_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const fadeOut = interpolate(
    frame,
    [durationFrames - TRANSITION_FRAMES, durationFrames],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill style={{ opacity: Math.min(fadeIn, fadeOut) }}>
      {children}
    </AbsoluteFill>
  );
};

export const OAuthDemo: React.FC = () => {
  // Convert durations to frames
  const scenes = [
    { Component: IntroScene, duration: INTRO_DURATION },
    { Component: AppIdentityScene, duration: APP_IDENTITY_DURATION },
    { Component: ConsentScreenScene, duration: CONSENT_SCREEN_DURATION },
    { Component: GmailReadonlyScene, duration: GMAIL_READONLY_DURATION },
    { Component: GmailModifyScene, duration: GMAIL_MODIFY_DURATION },
    { Component: GmailSendScene, duration: GMAIL_SEND_DURATION },
    { Component: CalendarScene, duration: CALENDAR_DURATION },
    { Component: YouTubeConnectionScene, duration: YOUTUBE_CONNECTION_DURATION },
    { Component: SecurityScene, duration: SECURITY_DURATION },
    { Component: OutroScene, duration: OUTRO_DURATION },
  ];

  let offset = 0;
  const sequences = scenes.map(({ Component, duration }, i) => {
    const durationFrames = duration * VIDEO_FPS;
    const from = offset;
    offset += durationFrames - TRANSITION_FRAMES;

    return (
      <Sequence key={i} from={from} durationInFrames={durationFrames}>
        <SceneWithTransition durationFrames={durationFrames}>
          <Component />
        </SceneWithTransition>
      </Sequence>
    );
  });

  return <AbsoluteFill style={{ backgroundColor: '#0a2e2e' }}>{sequences}</AbsoluteFill>;
};
