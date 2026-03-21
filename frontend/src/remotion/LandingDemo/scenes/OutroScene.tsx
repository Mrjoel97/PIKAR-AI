import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headingScale = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 80 },
  });
  const ctaOpacity = interpolate(frame, [fps * 2, fps * 3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const pulseScale = interpolate(frame % 60, [0, 30, 60], [1, 1.04, 1], {
    extrapolateRight: 'clamp',
  });
  const logoOpacity = interpolate(frame, [fps * 5, fps * 6], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#f8fafa',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Subtle teal glow */}
      <div
        style={{
          position: 'absolute',
          width: 800,
          height: 800,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(59, 191, 151, 0.08) 0%, transparent 70%)',
          filter: 'blur(100px)',
        }}
      />

      {/* Subtle grid pattern */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.03,
          backgroundImage: `linear-gradient(${COLORS.textDark} 1px, transparent 1px), linear-gradient(90deg, ${COLORS.textDark} 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
      />

      {/* Brain icon */}
      <div
        style={{
          width: 80,
          height: 80,
          borderRadius: 20,
          background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 32px rgba(26, 138, 110, 0.3)',
          marginBottom: 40,
          transform: `scale(${headingScale})`,
        }}
      >
        <span style={{ fontSize: 40 }}>{'\u{1F9E0}'}</span>
      </div>

      <div
        style={{
          fontSize: 64,
          fontWeight: 900,
          color: COLORS.textDark,
          fontFamily: FONTS.display,
          transform: `scale(${headingScale})`,
          textAlign: 'center',
          letterSpacing: -1,
          marginBottom: 20,
        }}
      >
        Ready to lead smarter?
      </div>

      <div
        style={{
          fontSize: 26,
          color: COLORS.textMuted,
          fontFamily: FONTS.body,
          marginBottom: 56,
        }}
      >
        Your AI executive team is waiting.
      </div>

      <div
        style={{
          opacity: ctaOpacity,
          transform: `scale(${pulseScale})`,
          padding: '22px 56px',
          borderRadius: 18,
          background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accentDark})`,
          boxShadow: '0 4px 24px rgba(59, 191, 151, 0.3)',
        }}
      >
        <span
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: COLORS.textDark,
            fontFamily: FONTS.display,
            letterSpacing: 0.5,
          }}
        >
          Start Free Trial
        </span>
      </div>

      {/* Logo at bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          opacity: logoOpacity,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ fontSize: 16 }}>{'\u{1F9E0}'}</span>
        </div>
        <span
          style={{
            fontSize: 20,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
          }}
        >
          Pikar <span style={{ color: COLORS.primary }}>AI</span>
        </span>
      </div>
    </AbsoluteFill>
  );
};
