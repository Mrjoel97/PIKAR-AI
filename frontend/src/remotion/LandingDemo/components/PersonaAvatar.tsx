import React from 'react';
import { useCurrentFrame, spring, useVideoConfig } from 'remotion';

interface PersonaAvatarProps {
  emoji: string;
  gradient: [string, string];
  size?: number;
  appearFrame?: number;
}

export const PersonaAvatar: React.FC<PersonaAvatarProps> = ({ emoji, gradient, size = 80, appearFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = Math.max(0, frame - appearFrame);
  const scale = spring({ frame: localFrame, fps, config: { damping: 12, stiffness: 100 } });

  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      transform: `scale(${scale})`,
      boxShadow: '0 4px 14px -2px rgba(0,0,0,0.25), 0 2px 4px -1px rgba(0,0,0,0.15)',
      border: '2px solid rgba(255,255,255,0.15)',
    }}>
      <span style={{ fontSize: size * 0.45 }}>{emoji}</span>
    </div>
  );
};
