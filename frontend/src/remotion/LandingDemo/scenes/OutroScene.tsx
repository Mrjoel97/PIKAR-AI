import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headingScale = spring({ frame, fps, config: { damping: 14, stiffness: 80 } });
  const ctaOpacity = interpolate(frame, [fps * 2, fps * 3], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const pulseScale = interpolate(frame % 60, [0, 30, 60], [1, 1.04, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      backgroundColor: COLORS.bgDark, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
    }}>
      {/* Teal glow */}
      <div style={{
        position: 'absolute', width: 800, height: 800, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(59, 191, 151, 0.1) 0%, transparent 70%)', filter: 'blur(100px)',
      }} />

      {/* Brain icon */}
      <div style={{
        width: 64, height: 64, borderRadius: 16,
        background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 4px 24px rgba(26, 138, 110, 0.4)',
        marginBottom: 32, transform: `scale(${headingScale})`,
      }}>
        <span style={{ fontSize: 32 }}>{'\u{1F9E0}'}</span>
      </div>

      <div style={{
        fontSize: 56, fontWeight: 900, color: COLORS.textPrimary,
        fontFamily: FONTS.display, transform: `scale(${headingScale})`,
        textAlign: 'center', letterSpacing: -1, marginBottom: 16,
      }}>
        Ready to lead smarter?
      </div>

      <div style={{
        fontSize: 22, color: COLORS.textSecondary,
        fontFamily: FONTS.body, marginBottom: 48,
      }}>
        Your AI executive team is waiting.
      </div>

      <div style={{
        opacity: ctaOpacity, transform: `scale(${pulseScale})`,
        padding: '18px 48px', borderRadius: 16,
        background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accentDark})`,
        boxShadow: '0 0 40px rgba(59, 191, 151, 0.4)',
      }}>
        <span style={{
          fontSize: 20, fontWeight: 700, color: COLORS.bgDark,
          fontFamily: FONTS.display, letterSpacing: 0.5,
        }}>
          Start Free Trial
        </span>
      </div>
    </AbsoluteFill>
  );
};
