import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS, AGENTS } from '../constants';

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- Brain icon springs in ---
  const logoSpring = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80 },
  });

  // --- "Pikar AI" scales up ---
  const titleScale = spring({
    frame: Math.max(0, frame - 10),
    fps,
    config: { damping: 14, stiffness: 70 },
  });

  // --- Subtitle fades in ---
  const subtitleOpacity = interpolate(frame, [fps * 1.5, fps * 2.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const subtitleY = interpolate(frame, [fps * 1.5, fps * 2.5], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // --- Pulsing teal glow ---
  const glowPulse = interpolate(frame % 60, [0, 30, 60], [0.06, 0.16, 0.06]);
  const glowScale = interpolate(frame % 60, [0, 30, 60], [1, 1.08, 1]);

  // --- Gradient background rotation ---
  const gradientAngle = interpolate(frame, [0, fps * 8], [0, 360], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `conic-gradient(from ${gradientAngle}deg at 50% 50%, #f8fafa, #eef6f4, #f0faf6, #f8fafa)`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
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

      {/* Pulsing teal glow behind the logo */}
      <div
        style={{
          position: 'absolute',
          width: 700,
          height: 700,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(59, 191, 151, ${glowPulse}) 0%, transparent 70%)`,
          filter: 'blur(80px)',
          transform: `scale(${glowScale})`,
        }}
      />

      {/* Floating particles */}
      {[
        { x: 180, startY: 820, size: 5 },
        { x: 420, startY: 900, size: 3 },
        { x: 700, startY: 860, size: 6 },
        { x: 960, startY: 940, size: 4 },
        { x: 1200, startY: 870, size: 3 },
        { x: 1450, startY: 910, size: 5 },
        { x: 1680, startY: 850, size: 4 },
        { x: 300, startY: 950, size: 3 },
      ].map((p, i) => {
        const yOffset = interpolate(frame, [0, fps * 8], [0, -450], {
          extrapolateRight: 'clamp',
        });
        const particleOpacity = interpolate(
          frame,
          [0, fps * 1.5, fps * 6.5, fps * 8],
          [0, 0.35, 0.35, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: p.x,
              top: p.startY + yOffset,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              backgroundColor: COLORS.accent,
              opacity: particleOpacity,
            }}
          />
        );
      })}

      {/* Brain emoji icon */}
      <div
        style={{
          width: 110,
          height: 110,
          borderRadius: 28,
          background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 12px 40px rgba(26, 138, 110, 0.35)',
          transform: `scale(${logoSpring})`,
          marginBottom: 36,
        }}
      >
        <span style={{ fontSize: 56 }}>{'\u{1F9E0}'}</span>
      </div>

      {/* "Pikar AI" title */}
      <div
        style={{
          fontSize: 88,
          fontWeight: 900,
          fontFamily: FONTS.display,
          transform: `scale(${titleScale})`,
          letterSpacing: -2,
          marginBottom: 16,
          lineHeight: 1,
        }}
      >
        <span style={{ color: COLORS.textDark }}>Pikar </span>
        <span style={{ color: COLORS.accent }}>AI</span>
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 36,
          fontWeight: 500,
          fontFamily: FONTS.body,
          color: COLORS.textMuted,
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          marginBottom: 64,
          letterSpacing: 0.5,
        }}
      >
        Your AI-Powered Executive Team
      </div>

      {/* 10 agent emoji icons - staggered spring */}
      <div
        style={{
          display: 'flex',
          gap: 28,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {AGENTS.map((agent, i) => {
          const agentSpring = spring({
            frame: Math.max(0, frame - (fps * 3 + i * 4)),
            fps,
            config: { damping: 10, stiffness: 120, mass: 0.8 },
          });
          const agentOpacity = interpolate(
            frame,
            [fps * 3 + i * 4, fps * 3 + i * 4 + 12],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          return (
            <div
              key={agent.name}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 10,
                opacity: agentOpacity,
                transform: `scale(${agentSpring}) translateY(${interpolate(agentSpring, [0, 1], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
              }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 18,
                  backgroundColor: '#ffffff',
                  border: `2px solid ${COLORS.border}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
                }}
              >
                <span style={{ fontSize: 34 }}>{agent.emoji}</span>
              </div>
              <span
                style={{
                  fontSize: 14,
                  fontFamily: FONTS.mono,
                  color: COLORS.textMuted,
                  fontWeight: 600,
                }}
              >
                {agent.name}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
