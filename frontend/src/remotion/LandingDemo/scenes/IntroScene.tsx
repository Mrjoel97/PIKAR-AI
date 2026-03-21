import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from 'remotion';
import { COLORS } from '../constants';
import { TypewriterText } from '../components/TypewriterText';

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80 },
  });
  const taglineOpacity = interpolate(frame, [fps * 2, fps * 3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const gradientAngle = interpolate(frame, [0, fps * 8], [0, 360]);

  return (
    <AbsoluteFill
      style={{
        background: `conic-gradient(from ${gradientAngle}deg at 50% 50%, ${COLORS.bgDark}, #0a1628, ${COLORS.bgDark})`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(13,204,242,0.15) 0%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />

      <div
        style={{
          fontSize: 72,
          fontWeight: 900,
          fontFamily: 'Inter, system-ui, sans-serif',
          transform: `scale(${logoScale})`,
          letterSpacing: -2,
          marginBottom: 16,
        }}
      >
        <span style={{ color: COLORS.accent }}>pikar</span>
        <span style={{ color: COLORS.textPrimary }}>.</span>
        <span style={{ color: COLORS.textPrimary }}>ai</span>
      </div>

      <div
        style={{
          opacity: taglineOpacity,
          fontSize: 24,
          color: COLORS.textSecondary,
          fontFamily: 'Inter, system-ui, sans-serif',
          fontWeight: 400,
          letterSpacing: 2,
          textTransform: 'uppercase' as const,
        }}
      >
        Your AI Executive Team
      </div>

      <Sequence from={Math.round(fps * 4)} layout="none">
        <div
          style={{
            marginTop: 40,
            padding: '16px 32px',
            borderRadius: 12,
            backgroundColor: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <TypewriterText
            text="10 specialized agents. 4 personas. One command."
            charsPerFrame={0.5}
            showCursor
            style={{
              fontSize: 20,
              color: COLORS.textPrimary,
              fontFamily: 'Inter, system-ui, sans-serif',
              fontWeight: 500,
            }}
          />
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};
