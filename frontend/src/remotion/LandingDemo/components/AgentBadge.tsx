import React from 'react';
import { useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS } from '../constants';

interface AgentBadgeProps {
  name: string;
  emoji: string;
  role: string;
  appearFrame: number;
  accentColor?: string;
}

export const AgentBadge: React.FC<AgentBadgeProps> = ({ name, emoji, role, appearFrame, accentColor = COLORS.accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - appearFrame;
  if (localFrame < 0) return null;

  const scale = spring({ frame: localFrame, fps, config: { damping: 15, stiffness: 150, mass: 0.4 } });
  const pulseOpacity = interpolate((frame % 60), [0, 30, 60], [0.4, 0.8, 0.4], { extrapolateRight: 'clamp' });

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px',
      borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.05)',
      border: '1px solid rgba(255,255,255,0.1)', transform: `scale(${scale})`, marginBottom: 8,
    }}>
      <span style={{ fontSize: 20 }}>{emoji}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.textPrimary, fontFamily: 'Inter, system-ui, sans-serif' }}>{name}</div>
        <div style={{ fontSize: 11, color: COLORS.textMuted, fontFamily: 'Inter, system-ui, sans-serif' }}>{role}</div>
      </div>
      <div style={{
        width: 8, height: 8, borderRadius: '50%', backgroundColor: '#22c55e',
        opacity: pulseOpacity, boxShadow: `0 0 6px rgba(34, 197, 94, ${pulseOpacity})`,
      }} />
    </div>
  );
};
