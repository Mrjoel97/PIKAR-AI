import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  staticFile,
} from 'remotion';
import { COLORS, FONTS } from '../constants';

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const titleOpacity = interpolate(frame, [fps * 0.8, fps * 1.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const titleY = interpolate(frame, [fps * 0.8, fps * 1.5], [30, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const subtitleOpacity = interpolate(frame, [fps * 1.8, fps * 2.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const badgeOpacity = interpolate(frame, [fps * 2.8, fps * 3.5], [0, 1], {
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
          width: 800,
          height: 800,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(59,191,151,${glowPulse}) 0%, transparent 70%)`,
          filter: 'blur(100px)',
        }}
      />

      {/* Grid */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.04,
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '80px 80px',
        }}
      />

      {/* Logo */}
      <div
        style={{
          transform: `scale(${logoScale})`,
          marginBottom: 32,
          width: 100,
          height: 100,
          borderRadius: 24,
          background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.teal600})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: `0 20px 60px rgba(43,168,143,0.4)`,
          fontSize: 48,
        }}
      >
        &#9733;
      </div>

      {/* Title */}
      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          fontFamily: FONTS.display,
          fontSize: 72,
          fontWeight: 700,
          color: COLORS.textPrimary,
          letterSpacing: -1,
        }}
      >
        Pikar AI
      </div>

      {/* Subtitle */}
      <div
        style={{
          opacity: subtitleOpacity,
          fontFamily: FONTS.body,
          fontSize: 32,
          color: COLORS.textSecondary,
          marginTop: 16,
        }}
      >
        OAuth Verification Demo
      </div>

      {/* Badge */}
      <div
        style={{
          opacity: badgeOpacity,
          marginTop: 40,
          padding: '12px 28px',
          borderRadius: 999,
          background: 'rgba(255,255,255,0.08)',
          border: '1px solid rgba(255,255,255,0.12)',
          fontFamily: FONTS.body,
          fontSize: 20,
          color: COLORS.textSecondary,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <span style={{ color: COLORS.googleBlue }}>G</span>
        <span style={{ color: COLORS.googleRed }}>o</span>
        <span style={{ color: COLORS.googleYellow }}>o</span>
        <span style={{ color: COLORS.googleBlue }}>g</span>
        <span style={{ color: COLORS.googleGreen }}>l</span>
        <span style={{ color: COLORS.googleRed }}>e</span>
        <span style={{ marginLeft: 4 }}>OAuth 2.0 Sensitive & Restricted Scopes</span>
      </div>
    </AbsoluteFill>
  );
};
