// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface NarrationLine {
  text: string;
  startFrame: number;
  endFrame: number;
}

interface NarrationOverlayProps {
  lines: NarrationLine[];
}

export const NarrationOverlay: React.FC<NarrationOverlayProps> = ({ lines }) => {
  const frame = useCurrentFrame();

  return (
    <>
      {lines.map((line, i) => {
        const fadeIn = interpolate(
          frame,
          [line.startFrame, line.startFrame + 20],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        const fadeOut = interpolate(
          frame,
          [line.endFrame - 20, line.endFrame],
          [1, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        const opacity = Math.min(fadeIn, fadeOut);
        const translateY = interpolate(fadeIn, [0, 1], [20, 0]);

        if (opacity <= 0) return null;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              bottom: 120,
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'center',
              opacity,
              transform: `translateY(${translateY}px)`,
            }}
          >
            <div
              style={{
                fontSize: 36,
                fontWeight: 600,
                color: COLORS.textDark,
                fontFamily: FONTS.display,
                textAlign: 'center',
                padding: '16px 48px',
                borderRadius: 16,
                backgroundColor: '#ffffff',
                border: `1px solid ${COLORS.border}`,
                boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
                maxWidth: 900,
              }}
            >
              {line.text}
            </div>
          </div>
        );
      })}
    </>
  );
};
