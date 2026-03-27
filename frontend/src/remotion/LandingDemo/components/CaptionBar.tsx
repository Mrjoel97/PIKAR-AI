// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface CaptionBarProps {
  text: string;
  appearFrame?: number;
}

export const CaptionBar: React.FC<CaptionBarProps> = ({ text, appearFrame = 15 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = Math.max(0, frame - appearFrame);
  const slideUp = spring({ frame: localFrame, fps, config: { damping: 20, stiffness: 100 } });
  const translateY = interpolate(slideUp, [0, 1], [40, 0]);
  const opacity = interpolate(localFrame, [0, 10], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0,
      transform: `translateY(${translateY}px)`, opacity,
      display: 'flex', flexDirection: 'column', alignItems: 'center',
    }}>
      {/* Teal accent line */}
      <div style={{
        width: 120, height: 2, borderRadius: 1,
        backgroundColor: COLORS.accent, marginBottom: 0,
      }} />
      <div style={{
        width: '100%', padding: '14px 32px',
        backgroundColor: 'rgba(10, 46, 46, 0.85)',
        borderTop: '1px solid rgba(59, 191, 151, 0.2)',
        display: 'flex', justifyContent: 'center',
      }}>
        <span style={{
          fontSize: 18, fontWeight: 600, color: COLORS.accent,
          fontFamily: FONTS.body, letterSpacing: 1,
        }}>{text}</span>
      </div>
    </div>
  );
};
