import React from 'react';
import { useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS } from '../constants';

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
      position: 'absolute', bottom: 40, left: '50%',
      transform: `translateX(-50%) translateY(${translateY}px)`, opacity,
      padding: '12px 32px', borderRadius: 999,
      backgroundColor: 'rgba(13, 204, 242, 0.12)',
      border: '1px solid rgba(13, 204, 242, 0.3)',
      backdropFilter: 'blur(8px)',
    }}>
      <span style={{
        fontSize: 18, fontWeight: 600, color: COLORS.accent,
        fontFamily: 'Inter, system-ui, sans-serif', letterSpacing: 0.5,
      }}>{text}</span>
    </div>
  );
};
