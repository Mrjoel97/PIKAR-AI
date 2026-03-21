import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Sequence } from 'remotion';
import { COLORS, FONTS } from '../constants';
import { TypewriterText } from '../components/TypewriterText';

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const taglineOpacity = interpolate(frame, [fps * 2, fps * 3], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const gradientAngle = interpolate(frame, [0, fps * 8], [0, 360]);

  return (
    <AbsoluteFill style={{
      background: `conic-gradient(from ${gradientAngle}deg at 50% 50%, ${COLORS.bgDark}, ${COLORS.bgHero}, ${COLORS.bgDark})`,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    }}>
      {/* Teal glow orb */}
      <div style={{
        position: 'absolute', width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(59, 191, 151, 0.15) 0%, transparent 70%)',
        filter: 'blur(80px)',
      }} />

      {/* Brain icon in gradient box */}
      <div style={{
        width: 80, height: 80, borderRadius: 20,
        background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 4px 24px rgba(26, 138, 110, 0.4)',
        transform: `scale(${logoScale})`, marginBottom: 24,
      }}>
        <span style={{ fontSize: 40 }}>{'\u{1F9E0}'}</span>
      </div>

      {/* Brand name */}
      <div style={{
        fontSize: 72, fontWeight: 900, fontFamily: FONTS.display,
        transform: `scale(${logoScale})`, letterSpacing: -2, marginBottom: 16,
      }}>
        <span style={{ color: COLORS.textPrimary }}>Pikar</span>
        <span style={{ color: COLORS.textPrimary }}> </span>
        <span style={{ color: COLORS.primary }}>AI</span>
      </div>

      {/* Tagline - matching real hero "Your AI-Powered Executive Team" */}
      <div style={{
        opacity: taglineOpacity, fontSize: 24, color: COLORS.textSecondary,
        fontFamily: FONTS.display, fontWeight: 400, letterSpacing: 2, textTransform: 'uppercase' as const,
      }}>
        Your AI-Powered Executive Team
      </div>

      {/* Typewriter subtitle */}
      <Sequence from={Math.round(fps * 4)} layout="none">
        <div style={{
          marginTop: 40, padding: '16px 32px', borderRadius: 12,
          backgroundColor: 'rgba(59, 191, 151, 0.08)',
          border: '1px solid rgba(59, 191, 151, 0.15)',
        }}>
          <TypewriterText
            text="10 specialized agents. 4 personas. One command."
            charsPerFrame={0.5} showCursor
            style={{ fontSize: 20, color: COLORS.textPrimary, fontFamily: FONTS.body, fontWeight: 500 }}
          />
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};
