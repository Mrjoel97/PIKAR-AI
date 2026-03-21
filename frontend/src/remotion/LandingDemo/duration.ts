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
 *   intro(12s) + 3x persona(30s) + executive(30s) + outro(10s) = 142s
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
