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
  PERSONA_DURATION,
  EXECUTIVE_DURATION,
  OUTRO_DURATION,
  TRANSITION_FRAMES,
} from './constants';
import { PERSONA_SCENES } from './data/personas';
import { IntroScene } from './scenes/IntroScene';
import { PersonaScene } from './scenes/PersonaScene';
import { OutroScene } from './scenes/OutroScene';

export { TOTAL_DURATION_FRAMES } from './duration';

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
        {/* Intro */}
        <TransitionSeries.Sequence durationInFrames={INTRO_DURATION * VIDEO_FPS}>
          <IntroScene />
        </TransitionSeries.Sequence>

        {/* Persona scenes */}
        {PERSONA_SCENES.map((persona) => {
          const duration = persona.id === 'enterprise' ? EXECUTIVE_DURATION : PERSONA_DURATION;
          return (
            <React.Fragment key={persona.id}>
              <TransitionSeries.Transition
                presentation={fade()}
                timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
              />
              <TransitionSeries.Sequence durationInFrames={duration * VIDEO_FPS}>
                <PersonaScene data={persona} />
              </TransitionSeries.Sequence>
            </React.Fragment>
          );
        })}

        {/* Outro */}
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
        <TransitionSeries.Sequence durationInFrames={OUTRO_DURATION * VIDEO_FPS}>
          <OutroScene />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
