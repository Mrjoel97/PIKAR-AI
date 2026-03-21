// frontend/src/remotion/LandingDemo/duration.ts
// Extracted so tests can import without pulling in Remotion React deps.
import {
  VIDEO_FPS,
  INTRO_DURATION,
  PERSONA_DURATION,
  EXECUTIVE_DURATION,
  OUTRO_DURATION,
  TRANSITION_FRAMES,
} from './constants';
import { PERSONA_SCENES } from './data/personas';

/**
 * Total duration in frames:
 *   intro(8s) + 3x persona(25s) + executive(30s) + outro(8s) = 121s
 *   minus overlapping transitions
 */
const sceneDurations = [
  INTRO_DURATION,
  ...PERSONA_SCENES.map((p) => (p.id === 'enterprise' ? EXECUTIVE_DURATION : PERSONA_DURATION)),
  OUTRO_DURATION,
];

export const TOTAL_DURATION_FRAMES =
  sceneDurations.reduce((sum, d) => sum + d * VIDEO_FPS, 0) -
  (sceneDurations.length - 1) * TRANSITION_FRAMES;
