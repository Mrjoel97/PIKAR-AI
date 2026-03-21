import React from 'react';
import { useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface FloatingMetricProps {
  label: string;
  value: string;
  trend: 'up' | 'down' | 'flat';
  appearFrame: number;
  index: number;
}

export const FloatingMetric: React.FC<FloatingMetricProps> = ({
  label,
  value,
  trend,
  appearFrame,
  index: _index,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const relFrame = frame - appearFrame;
  if (relFrame < 0) return null;

  const scale = spring({
    frame: relFrame,
    fps,
    config: { damping: 15, stiffness: 100 },
  });
  const opacity = interpolate(relFrame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const trendColor =
    trend === 'up'
      ? '#22c55e'
      : trend === 'down'
        ? '#ef4444'
        : COLORS.textDark;
  const trendArrow = trend === 'up' ? '\u2191' : trend === 'down' ? '\u2193' : '';

  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        padding: '16px 24px',
        borderRadius: 16,
        backgroundColor: '#ffffff',
        border: `1px solid ${COLORS.border}`,
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        minWidth: 160,
      }}
    >
      <div
        style={{
          fontSize: 13,
          color: COLORS.textMuted,
          fontFamily: FONTS.mono,
          textTransform: 'uppercase' as const,
          letterSpacing: 1,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 800,
          color: trendColor,
          fontFamily: FONTS.mono,
        }}
      >
        {value} {trendArrow}
      </div>
    </div>
  );
};
