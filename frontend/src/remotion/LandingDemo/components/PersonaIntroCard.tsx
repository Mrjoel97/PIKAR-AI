import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface PersonaIntroCardProps {
  title: string;
  subtitle: string;
  emoji: string;
  gradient: [string, string];
  tierFeatures: string[];
}

export const PersonaIntroCard: React.FC<PersonaIntroCardProps> = ({
  title,
  subtitle,
  emoji,
  gradient,
  tierFeatures,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const exitOpacity = interpolate(frame, [140, 165], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  if (frame > 165) return null;

  const emojiScale = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 60 },
  });
  const titleOpacity = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const subtitleOpacity = interpolate(frame, [30, 45], [0, 1], {
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
        opacity: exitOpacity,
      }}
    >
      {/* Colored accent glow behind emoji */}
      <div
        style={{
          position: 'absolute',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${gradient[0]}30 0%, transparent 70%)`,
          filter: 'blur(60px)',
          top: '15%',
        }}
      />

      {/* Animated shimmer scan line */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: interpolate(frame, [0, 120], [-200, 2200], {
            extrapolateRight: 'clamp',
          }),
          width: 200,
          height: '100%',
          background:
            'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
          pointerEvents: 'none',
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

      <div
        style={{
          fontSize: 100,
          transform: `scale(${emojiScale})`,
          marginBottom: 24,
          filter: 'drop-shadow(0 8px 24px rgba(0,0,0,0.1))',
        }}
      >
        {emoji}
      </div>

      <div
        style={{
          opacity: titleOpacity,
          fontSize: 72,
          fontWeight: 900,
          fontFamily: FONTS.display,
          color: COLORS.textDark,
          letterSpacing: -2,
          marginBottom: 12,
        }}
      >
        {title}
      </div>

      <div
        style={{
          opacity: subtitleOpacity,
          fontSize: 24,
          fontWeight: 400,
          fontFamily: FONTS.body,
          color: COLORS.textMuted,
          letterSpacing: 1,
          marginBottom: 40,
        }}
      >
        {subtitle}
      </div>

      {/* Tier features */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          alignItems: 'flex-start',
        }}
      >
        {tierFeatures.map((feature, i) => {
          const featureOpacity = interpolate(
            frame,
            [45 + i * 12, 55 + i * 12],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const slideX = interpolate(featureOpacity, [0, 1], [20, 0]);
          return (
            <div
              key={i}
              style={{
                opacity: featureOpacity,
                transform: `translateX(${slideX}px)`,
                display: 'flex',
                alignItems: 'center',
                gap: 14,
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
                  boxShadow: `0 0 8px ${gradient[0]}40`,
                }}
              />
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 500,
                  color: COLORS.textDark,
                  fontFamily: FONTS.body,
                }}
              >
                {feature}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
