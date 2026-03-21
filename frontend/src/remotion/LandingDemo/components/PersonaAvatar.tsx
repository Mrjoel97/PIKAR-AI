import React from 'react';
import { useCurrentFrame, spring, useVideoConfig, interpolate } from 'remotion';

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
  const glowOpacity = interpolate(frame % 90, [0, 45, 90], [0.3, 0.6, 0.3], { extrapolateRight: 'clamp' });

  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      transform: `scale(${scale})`,
      boxShadow: `0 0 ${size / 2}px rgba(13, 204, 242, ${glowOpacity})`,
    }}>
      <span style={{ fontSize: size * 0.45 }}>{emoji}</span>
    </div>
  );
};
