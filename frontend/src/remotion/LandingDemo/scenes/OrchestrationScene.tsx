// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS, AGENTS } from '../constants';

/* ── Layout ─────────────────────────────────────────────── */
const CENTER_X = 960;
const CENTER_Y = 460;
const RING_RADIUS = 280;
const AGENT_CIRCLE_R = 46;
const STAGGER = 20; // frames between each agent appearing

/* ── Agent accent colors (one per agent, cycling teal palette) */
const ACCENT_COLORS = [
  COLORS.teal300,
  COLORS.teal400,
  COLORS.teal500,
  COLORS.teal600,
  COLORS.teal700,
  COLORS.teal800,
  COLORS.teal900,
  COLORS.teal200,
  COLORS.teal100,
  COLORS.teal50,
];

export const OrchestrationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* ── Background ───────────────────────────────────────── */
  const gradientAngle = interpolate(frame, [0, 420], [0, 25]);

  /* ── Badge fade-in ────────────────────────────────────── */
  const badgeOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  /* ── Center hub ───────────────────────────────────────── */
  const hubScale = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 70 },
  });

  /* ── Task counter (starts at frame 200, counts to 47) ── */
  const COUNTER_START = 200;
  const COUNTER_END = 380;
  const rawCount = interpolate(
    frame,
    [COUNTER_START, COUNTER_END],
    [0, 47],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  const taskCount = Math.round(rawCount);
  const counterOpacity = interpolate(
    frame,
    [COUNTER_START, COUNTER_START + 20],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  return (
    <AbsoluteFill
      style={{
        background: `conic-gradient(from ${gradientAngle}deg at 50% 50%, #f8fafa, #eef6f4, #f8fafa)`,
      }}
    >
      {/* Ambient glow */}
      <div
        style={{
          position: 'absolute',
          top: CENTER_Y - 350,
          left: CENTER_X - 350,
          width: 700,
          height: 700,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(59,191,151,0.08) 0%, transparent 70%)',
          filter: 'blur(100px)',
        }}
      />

      {/* Grid pattern */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.03,
          backgroundImage: `linear-gradient(${COLORS.textDark} 1px, transparent 1px), linear-gradient(90deg, ${COLORS.textDark} 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
      />

      {/* ── Time badge (top-left) ─────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 36,
          left: 48,
          opacity: badgeOpacity,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 22px',
          borderRadius: 14,
          backgroundColor: 'rgba(255,255,255,0.85)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <span style={{ fontSize: 22 }}>{'\u{1F451}'}</span>
        <span
          style={{
            fontSize: 22,
            fontWeight: 700,
            fontFamily: FONTS.mono,
            color: COLORS.textDark,
          }}
        >
          3:00 PM
        </span>
      </div>

      {/* ═══════════════════════════════════════════════════════
          CONNECTING LINES — rendered first (behind circles)
          ═══════════════════════════════════════════════════════ */}
      <svg
        width={1920}
        height={1080}
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      >
        {AGENTS.map((_, i) => {
          const angle = (i / AGENTS.length) * Math.PI * 2 - Math.PI / 2;
          const ax = CENTER_X + RING_RADIUS * Math.cos(angle);
          const ay = CENTER_Y + RING_RADIUS * Math.sin(angle);

          // Lines appear after all agents visible (~frame 200)
          const allVisibleFrame = AGENTS.length * STAGGER + 30;
          const pulsePhase = ((frame - allVisibleFrame + i * 12) % 60) / 60;
          const lineOpacity = interpolate(
            frame,
            [allVisibleFrame, allVisibleFrame + 30],
            [0, 0.15 + 0.15 * Math.sin(pulsePhase * Math.PI * 2)],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          // Animated data dot traveling from center to agent
          const dotProgress = interpolate(
            (frame - allVisibleFrame + i * 8) % 80,
            [0, 80],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const dotX = CENTER_X + (ax - CENTER_X) * dotProgress;
          const dotY = CENTER_Y + (ay - CENTER_Y) * dotProgress;
          const dotOpacity = frame >= allVisibleFrame
            ? interpolate(dotProgress, [0, 0.1, 0.9, 1], [0, 0.7, 0.7, 0], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              })
            : 0;

          return (
            <React.Fragment key={`line-${i}`}>
              <line
                x1={CENTER_X}
                y1={CENTER_Y}
                x2={ax}
                y2={ay}
                stroke={COLORS.accent}
                strokeWidth={2}
                opacity={lineOpacity}
              />
              <circle
                cx={dotX}
                cy={dotY}
                r={4}
                fill={COLORS.accent}
                opacity={dotOpacity}
              />
            </React.Fragment>
          );
        })}
      </svg>

      {/* ═══════════════════════════════════════════════════════
          CENTER HUB — Executive Agent
          ═══════════════════════════════════════════════════════ */}
      <div
        style={{
          position: 'absolute',
          left: CENTER_X - 52,
          top: CENTER_Y - 52,
          width: 104,
          height: 104,
          borderRadius: '50%',
          background: `radial-gradient(circle at 35% 35%, ${COLORS.teal500}, ${COLORS.teal800})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(26,138,110,0.2), 0 12px 40px rgba(26,138,110,0.35), inset 0 2px 4px rgba(255,255,255,0.2)',
          transform: `scale(${hubScale})`,
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: 48 }}>{'\u{1F451}'}</span>
      </div>
      {/* Hub label */}
      <div
        style={{
          position: 'absolute',
          left: CENTER_X - 80,
          top: CENTER_Y + 60,
          width: 160,
          textAlign: 'center',
          opacity: hubScale,
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontSize: 15,
            fontWeight: 700,
            fontFamily: FONTS.body,
            color: COLORS.textDark,
          }}
        >
          Executive Agent
        </span>
      </div>

      {/* ═══════════════════════════════════════════════════════
          AGENT RING
          ═══════════════════════════════════════════════════════ */}
      {AGENTS.map((agent, i) => {
        const angle = (i / AGENTS.length) * Math.PI * 2 - Math.PI / 2;
        const ax = CENTER_X + RING_RADIUS * Math.cos(angle);
        const ay = CENTER_Y + RING_RADIUS * Math.sin(angle);

        const agentAppear = 30 + i * STAGGER;
        const agentScale = spring({
          frame: Math.max(0, frame - agentAppear),
          fps,
          config: { damping: 12, stiffness: 100 },
        });

        // Status glow — after frame 200, staggered
        const statusStart = 210 + i * 18;
        const glowOpacity = interpolate(
          frame,
          [statusStart, statusStart + 15, statusStart + 50],
          [0, 0.6, 0.15],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        const statusOpacity = interpolate(
          frame,
          [statusStart + 10, statusStart + 25],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );

        return (
          <React.Fragment key={agent.name}>
            {/* Agent circle */}
            <div
              style={{
                position: 'absolute',
                left: ax - AGENT_CIRCLE_R,
                top: ay - AGENT_CIRCLE_R,
                width: AGENT_CIRCLE_R * 2,
                height: AGENT_CIRCLE_R * 2,
                borderRadius: '50%',
                backgroundColor: '#ffffff',
                border: '2.5px solid rgba(226,232,240,0.8)',
                boxShadow: `0 3px 16px rgba(0,0,0,0.06), 0 0 ${glowOpacity > 0.1 ? 24 : 0}px ${ACCENT_COLORS[i]}60, 0 0 ${glowOpacity > 0.1 ? 48 : 0}px ${ACCENT_COLORS[i]}30, inset 0 1px 3px rgba(0,0,0,0.04)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transform: `scale(${agentScale})`,
                zIndex: 5,
              }}
            >
              <span style={{ fontSize: 32 }}>{agent.emoji}</span>
            </div>

            {/* Agent name */}
            <div
              style={{
                position: 'absolute',
                left: ax - 60,
                top: ay + AGENT_CIRCLE_R + 6,
                width: 120,
                textAlign: 'center',
                opacity: agentScale,
                zIndex: 5,
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  fontFamily: FONTS.body,
                  color: COLORS.textDark,
                }}
              >
                {agent.name}
              </span>
            </div>

            {/* Status check */}
            {frame >= statusStart + 10 && (
              <div
                style={{
                  position: 'absolute',
                  left: ax + AGENT_CIRCLE_R + 4,
                  top: ay - 10,
                  opacity: statusOpacity,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '3px 10px',
                  borderRadius: 8,
                  backgroundColor: 'rgba(34,197,94,0.12)',
                  backdropFilter: 'blur(8px)',
                  boxShadow: '0 2px 8px rgba(34,197,94,0.15)',
                  zIndex: 6,
                }}
              >
                <span
                  style={{
                    fontSize: 14,
                    color: '#16a34a',
                    fontWeight: 700,
                    fontFamily: FONTS.mono,
                  }}
                >
                  {'\u2713'} Complete
                </span>
              </div>
            )}
          </React.Fragment>
        );
      })}

      {/* ═══════════════════════════════════════════════════════
          TASK COUNTER — bottom center
          ═══════════════════════════════════════════════════════ */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: counterOpacity,
        }}
      >
        <div
          style={{
            padding: '28px 56px',
            borderRadius: 24,
            backgroundColor: 'rgba(255,255,255,0.7)',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 12,
            }}
          >
            <span
              style={{
                fontSize: 72,
                fontWeight: 900,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
                letterSpacing: -2,
                fontVariantNumeric: 'tabular-nums',
                textShadow: '0 1px 8px rgba(0,0,0,0.06)',
              }}
            >
              {taskCount}
            </span>
            <span
              style={{
                fontSize: 32,
                fontWeight: 700,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
              }}
            >
              tasks completed today
            </span>
          </div>
          <span
            style={{
              fontSize: 20,
              fontFamily: FONTS.body,
              color: COLORS.textMuted,
              marginTop: 4,
            }}
          >
            across 10 departments
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
