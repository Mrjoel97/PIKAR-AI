// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface AgentBadgeProps {
  name: string;
  emoji: string;
  role: string;
  appearFrame: number;
}

export const AgentBadge: React.FC<AgentBadgeProps> = ({ name, emoji, role, appearFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - appearFrame;
  if (localFrame < 0) return null;

  const scale = spring({ frame: localFrame, fps, config: { damping: 15, stiffness: 150, mass: 0.4 } });
  const pulseOpacity = interpolate((frame % 60), [0, 30, 60], [0.4, 0.8, 0.4], { extrapolateRight: 'clamp' });
  const glowIntensity = interpolate(localFrame, [0, 20], [0.3, 0], { extrapolateRight: 'clamp' });

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px',
      borderRadius: 12,
      backgroundColor: 'rgba(59, 191, 151, 0.08)',
      border: '1px solid rgba(59, 191, 151, 0.15)',
      transform: `scale(${scale})`, marginBottom: 8,
      boxShadow: glowIntensity > 0 ? `0 0 12px rgba(59, 191, 151, ${glowIntensity})` : 'none',
    }}>
      <span style={{ fontSize: 20 }}>{emoji}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.textPrimary, fontFamily: FONTS.body }}>{name}</div>
        <div style={{ fontSize: 11, color: COLORS.textMuted, fontFamily: FONTS.mono }}>{role}</div>
      </div>
      <div style={{
        width: 8, height: 8, borderRadius: '50%', backgroundColor: '#22c55e',
        opacity: pulseOpacity, boxShadow: `0 0 6px rgba(34, 197, 94, ${pulseOpacity})`,
      }} />
    </div>
  );
};
