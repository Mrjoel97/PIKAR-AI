import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { COLORS, FONTS } from '../constants';
import { NarrationOverlay } from '../components/NarrationOverlay';

const NARRATION_LINES = [
  { text: 'Meet Pikar AI', startFrame: 0, endFrame: 90 },
  { text: 'Your AI-powered executive team', startFrame: 90, endFrame: 180 },
  { text: '10 specialized agents working together', startFrame: 180, endFrame: 270 },
  { text: 'Built for every stage of your business', startFrame: 270, endFrame: 360 },
];

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80 },
  });
  const glowPulse = interpolate(frame % 60, [0, 30, 60], [0.08, 0.15, 0.08]);
  const gradientAngle = interpolate(frame, [0, fps * 12], [0, 360]);

  return (
    <AbsoluteFill
      style={{
        background: `conic-gradient(from ${gradientAngle}deg at 50% 50%, #f8fafa, #eef6f4, #f8fafa)`,
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
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(59, 191, 151, ${glowPulse}) 0%, transparent 70%)`,
          filter: 'blur(80px)',
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
          width: 100,
          height: 100,
          borderRadius: 24,
          background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 32px rgba(26, 138, 110, 0.3)',
          transform: `scale(${logoScale})`,
          marginBottom: 32,
        }}
      >
        <span style={{ fontSize: 50 }}>{'\u{1F9E0}'}</span>
      </div>

      {/* Brand name */}
      <div
        style={{
          fontSize: 80,
          fontWeight: 900,
          fontFamily: FONTS.display,
          transform: `scale(${logoScale})`,
          letterSpacing: -2,
          marginBottom: 20,
        }}
      >
        <span style={{ color: COLORS.textDark }}>Pikar</span>
        <span style={{ color: COLORS.textDark }}> </span>
        <span style={{ color: COLORS.primary }}>AI</span>
      </div>

      {/* Floating particles */}
      {[
        { x: 200, startY: 800, size: 4 },
        { x: 500, startY: 900, size: 3 },
        { x: 800, startY: 850, size: 5 },
        { x: 1100, startY: 950, size: 3 },
        { x: 1400, startY: 880, size: 4 },
        { x: 1700, startY: 920, size: 3 },
      ].map((p, i) => {
        const yOffset = interpolate(frame, [0, fps * 12], [0, -400]);
        const particleOpacity = interpolate(
          frame,
          [0, fps * 2, fps * 10, fps * 12],
          [0, 0.3, 0.3, 0],
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

      {/* Narration overlay */}
      <NarrationOverlay lines={NARRATION_LINES} />
    </AbsoluteFill>
  );
};
