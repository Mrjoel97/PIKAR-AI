// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface TypingIndicatorProps {
  appearFrame: number;
  agentName?: string;
  agentEmoji?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  appearFrame,
  agentName,
  agentEmoji,
}) => {
  const frame = useCurrentFrame();
  const relFrame = frame - appearFrame;
  if (relFrame < 0) return null;

  const opacity = interpolate(relFrame, [0, 10], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        opacity,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '8px 0',
      }}
    >
      {agentName && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>{agentEmoji}</span>
          <span
            style={{
              fontSize: 14,
              color: COLORS.accent,
              fontFamily: FONTS.mono,
              fontWeight: 600,
            }}
          >
            {agentName}
          </span>
        </div>
      )}
      <div
        style={{
          display: 'flex',
          gap: 6,
          padding: '12px 20px',
          borderRadius: 16,
          backgroundColor: 'rgba(0,0,0,0.04)',
        }}
      >
        {[0, 1, 2].map((i) => {
          const bounce = interpolate(
            (relFrame + i * 5) % 30,
            [0, 10, 20, 30],
            [0, -8, 0, 0],
            { extrapolateRight: 'clamp' },
          );
          return (
            <div
              key={i}
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: COLORS.accent,
                transform: `translateY(${bounce}px)`,
                opacity: 0.7,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
