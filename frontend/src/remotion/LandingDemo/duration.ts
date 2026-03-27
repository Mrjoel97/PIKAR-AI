// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { VIDEO_FPS, SCENE_DURATIONS, TRANSITION_FRAMES } from './constants';

/**
 * Total duration in frames:
 *   8 scenes minus overlapping transitions
 */
export const TOTAL_DURATION_FRAMES =
  SCENE_DURATIONS.reduce((sum, d) => sum + d * VIDEO_FPS, 0) -
  (SCENE_DURATIONS.length - 1) * TRANSITION_FRAMES;
