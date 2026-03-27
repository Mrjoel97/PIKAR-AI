import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS } from '../constants';

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const textOpacity = interpolate(frame, [fps * 0.5, fps * 1.2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const subtitleOpacity = interpolate(frame, [fps * 1.5, fps * 2.2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const glowPulse = interpolate(frame % 90, [0, 45, 90], [0.08, 0.18, 0.08]);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${COLORS.bgDark} 0%, ${COLORS.teal900} 50%, ${COLORS.bgDark} 100%)`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Glow */}
      <div
        style={{
          position: 'absolute',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(59,191,151,${glowPulse}) 0%, transparent 70%)`,
          filter: 'blur(80px)',
        }}
      />

      {/* Logo */}
      <div
        style={{
          transform: `scale(${logoScale})`,
          marginBottom: 24,
          width: 80,
          height: 80,
          borderRadius: 20,
          background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.teal600})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: `0 16px 48px rgba(43,168,143,0.4)`,
          fontSize: 40,
        }}
      >
        &#9733;
      </div>

      <div
        style={{
          opacity: textOpacity,
          fontFamily: FONTS.display,
          fontSize: 52,
          fontWeight: 700,
          color: COLORS.textPrimary,
          marginBottom: 16,
        }}
      >
        Thank You
      </div>

      <div
        style={{
          opacity: subtitleOpacity,
          fontFamily: FONTS.body,
          fontSize: 24,
          color: COLORS.textSecondary,
          textAlign: 'center',
          lineHeight: 1.6,
        }}
      >
        Pikar AI — OAuth Verification Demo
        <br />
        <span style={{ fontSize: 18, color: COLORS.textMuted }}>
          pikar.ai
        </span>
      </div>
    </AbsoluteFill>
  );
};
