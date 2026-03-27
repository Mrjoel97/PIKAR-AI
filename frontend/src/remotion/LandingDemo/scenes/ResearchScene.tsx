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
import { COLORS, FONTS } from '../constants';

/* ── Source data ────────────────────────────────────────── */
const SOURCES = [
  { label: 'Web Search', icon: '🔍' },
  { label: 'Industry Reports', icon: '📑' },
  { label: 'Patent Database', icon: '📜' },
  { label: 'News Feed', icon: '📰' },
  { label: 'Social Signals', icon: '📡' },
];

const FINDINGS = [
  '3 new entrants identified',
  'Market share shift: 12% movement',
  'Pricing pressure in enterprise segment',
];

const GRAPH_NODES = [
  { label: 'APAC', cx: 960, cy: 820 },
  { label: 'Pricing', cx: 860, cy: 770 },
  { label: 'Competitors', cx: 1060, cy: 770 },
  { label: 'Enterprise', cx: 890, cy: 880 },
  { label: 'Growth', cx: 1030, cy: 880 },
];

const GRAPH_EDGES: [number, number][] = [
  [0, 1],
  [0, 2],
  [0, 3],
  [0, 4],
  [1, 3],
  [2, 4],
  [3, 4],
];

/* ── Helpers ────────────────────────────────────────────── */
const QUERY_TEXT = 'Analyze competitor landscape in APAC region';

export const ResearchScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* ── Background ───────────────────────────────────────── */
  const gradientAngle = interpolate(frame, [0, 420], [0, 30]);

  /* ── Time badge / agent badge ─────────────────────────── */
  const badgeOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  /* ── Phase 1: Search query (0-150) ────────────────────── */
  const queryBarY = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 80 },
  });
  // Typing effect — reveal characters one by one
  const charsVisible = Math.min(
    QUERY_TEXT.length,
    Math.floor(
      interpolate(frame, [15, 100], [0, QUERY_TEXT.length], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      }),
    ),
  );
  const typedText = QUERY_TEXT.slice(0, charsVisible);
  const cursorOpacity = frame % 30 < 15 ? 1 : 0;

  /* ── Phase 2: Report card (150-300) ───────────────────── */
  const reportY = interpolate(frame, [155, 195], [60, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const reportOpacity = interpolate(frame, [155, 185], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  /* ── Phase 3: Knowledge graph (300-420) ───────────────── */
  const graphOpacity = interpolate(frame, [300, 330], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `conic-gradient(from ${gradientAngle}deg at 50% 50%, #f8fafa, #eef6f4, #f8fafa)`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      {/* Ambient glow */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          width: 700,
          height: 700,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(59,191,151,0.07) 0%, transparent 70%)',
          filter: 'blur(90px)',
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
          backgroundColor: 'rgba(255,255,255,0.9)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <span style={{ fontSize: 22 }}>{'\u{1F9ED}'}</span>
        <span
          style={{
            fontSize: 22,
            fontWeight: 700,
            fontFamily: FONTS.mono,
            color: COLORS.textDark,
          }}
        >
          1:30 PM
        </span>
      </div>

      {/* ── Agent badge (top-right) ───────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 36,
          right: 48,
          opacity: badgeOpacity,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 22px',
          borderRadius: 14,
          backgroundColor: 'rgba(255,255,255,0.9)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <span
          style={{
            fontSize: 20,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
          }}
        >
          Strategic Agent
        </span>
        <span style={{ fontSize: 22 }}>{'\u{1F9ED}'}</span>
      </div>

      {/* ═══════════════════════════════════════════════════════
          PHASE 1 — Search query + source cards (0-150)
          ═══════════════════════════════════════════════════════ */}

      {/* Search bar */}
      <div
        style={{
          marginTop: 120,
          width: 860,
          padding: '20px 32px',
          borderRadius: 18,
          backgroundColor: '#ffffff',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.8)',
          border: '2px solid rgba(59,191,151,0.2)',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          transform: `translateY(${interpolate(queryBarY, [0, 1], [40, 0])}px)`,
          opacity: interpolate(queryBarY, [0, 1], [0, 1]),
        }}
      >
        <span style={{ fontSize: 26, opacity: 0.6 }}>{'\u{1F50D}'}</span>
        <span
          style={{
            fontSize: 24,
            fontFamily: FONTS.body,
            color: COLORS.textDark,
            fontWeight: 500,
          }}
        >
          {typedText}
          <span
            style={{
              display: 'inline-block',
              width: 2,
              height: 26,
              backgroundColor: COLORS.accent,
              marginLeft: 2,
              verticalAlign: 'middle',
              opacity: charsVisible < QUERY_TEXT.length ? cursorOpacity : 0,
            }}
          />
        </span>
      </div>

      {/* Source cards — fan pattern */}
      <div
        style={{
          position: 'relative',
          width: 900,
          height: 140,
          marginTop: 36,
        }}
      >
        {SOURCES.map((src, i) => {
          const activateFrame = 60 + i * 18;
          const cardSpring = spring({
            frame: Math.max(0, frame - activateFrame),
            fps,
            config: { damping: 12, stiffness: 90 },
          });
          // Fan spread: distribute across width
          const totalWidth = 820;
          const cardWidth = 148;
          const spacing = (totalWidth - cardWidth) / (SOURCES.length - 1);
          const xPos = i * spacing;
          // Slight arc — middle cards higher
          const arcY =
            -12 * Math.sin(((i / (SOURCES.length - 1)) * Math.PI));

          const glowOpacity = interpolate(
            frame,
            [activateFrame, activateFrame + 15, activateFrame + 40],
            [0, 0.5, 0.15],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          // Collapse toward center in Phase 2
          const collapseProgress = interpolate(
            frame,
            [150, 190],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const centerX = totalWidth / 2 - cardWidth / 2;
          const finalX = xPos + (centerX - xPos) * collapseProgress;
          const collapseOpacity = interpolate(
            frame,
            [160, 195],
            [1, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          return (
            <div
              key={src.label}
              style={{
                position: 'absolute',
                left: finalX + 40,
                top: 10 + arcY,
                width: cardWidth,
                padding: '14px 12px',
                borderRadius: 16,
                backgroundColor: '#ffffff',
                backdropFilter: 'blur(4px)',
                boxShadow: `0 2px 8px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.06), 0 0 ${glowOpacity > 0.1 ? 20 : 0}px rgba(59,191,151,${glowOpacity})`,
                border: `1.5px solid ${glowOpacity > 0.1 ? COLORS.accent : COLORS.border}`,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 6,
                transform: `scale(${cardSpring}) translateY(${interpolate(cardSpring, [0, 1], [20, 0])}px)`,
                opacity: collapseOpacity * cardSpring,
              }}
            >
              <span style={{ fontSize: 28 }}>{src.icon}</span>
              <span
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  fontFamily: FONTS.body,
                  color: COLORS.textDark,
                  textAlign: 'center',
                }}
              >
                {src.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════════
          PHASE 2 — Research report card (150-300)
          ═══════════════════════════════════════════════════════ */}
      {frame >= 150 && (
        <div
          style={{
            position: 'absolute',
            top: 300,
            width: 720,
            padding: '36px 44px',
            borderRadius: 22,
            backgroundColor: '#ffffff',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06), 0 24px 48px rgba(0,0,0,0.08)',
            border: `1.5px solid ${COLORS.border}`,
            borderTop: `3px solid ${COLORS.accent}`,
            opacity: reportOpacity,
            transform: `translateY(${reportY}px)`,
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              marginBottom: 28,
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 12,
                background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal500})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ fontSize: 24 }}>{'\u{1F4CB}'}</span>
            </div>
            <span
              style={{
                fontSize: 28,
                fontWeight: 800,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
              }}
            >
              APAC Competitive Analysis
            </span>
          </div>

          {/* Findings */}
          {FINDINGS.map((finding, i) => {
            const findingDelay = 180 + i * 30;
            const findingOpacity = interpolate(
              frame,
              [findingDelay, findingDelay + 20],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
            );
            const findingX = interpolate(
              frame,
              [findingDelay, findingDelay + 20],
              [20, 0],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
            );
            return (
              <div
                key={finding}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  marginBottom: 18,
                  opacity: findingOpacity,
                  transform: `translateX(${findingX}px)`,
                }}
              >
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 8,
                    background: 'linear-gradient(135deg, rgba(34,197,94,0.08), rgba(34,197,94,0.16))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <span
                    style={{
                      fontSize: 18,
                      color: '#16a34a',
                      fontWeight: 700,
                    }}
                  >
                    {'\u2713'}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 22,
                    fontFamily: FONTS.body,
                    color: COLORS.textDark,
                    fontWeight: 500,
                  }}
                >
                  {finding}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          PHASE 3 — Knowledge graph (300-420)
          ═══════════════════════════════════════════════════════ */}
      {frame >= 295 && (
        <div
          style={{
            position: 'absolute',
            bottom: 40,
            left: 0,
            right: 0,
            height: 220,
            opacity: graphOpacity,
          }}
        >
          <svg
            width={1920}
            height={220}
            viewBox="660 710 600 210"
            style={{ position: 'absolute', top: 0, left: 0 }}
          >
            {/* Edges */}
            {GRAPH_EDGES.map(([a, b], i) => {
              const edgeDelay = 310 + i * 10;
              const lineOpacity = interpolate(
                frame,
                [edgeDelay, edgeDelay + 20],
                [0, 0.35],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
              );
              return (
                <line
                  key={`e-${i}`}
                  x1={GRAPH_NODES[a].cx}
                  y1={GRAPH_NODES[a].cy}
                  x2={GRAPH_NODES[b].cx}
                  y2={GRAPH_NODES[b].cy}
                  stroke={COLORS.accent}
                  strokeWidth={2}
                  opacity={lineOpacity}
                />
              );
            })}

            {/* Nodes */}
            {GRAPH_NODES.map((node, i) => {
              const nodeDelay = 305 + i * 12;
              const nodeScale = spring({
                frame: Math.max(0, frame - nodeDelay),
                fps,
                config: { damping: 12, stiffness: 100 },
              });
              // Soft pulse
              const pulse = interpolate(
                (frame + i * 10) % 60,
                [0, 30, 60],
                [1, 1.12, 1],
                { extrapolateRight: 'clamp' },
              );
              return (
                <g
                  key={node.label}
                  transform={`translate(${node.cx}, ${node.cy}) scale(${nodeScale * pulse})`}
                >
                  <circle
                    r={28}
                    fill={COLORS.accent}
                    opacity={0.06}
                  />
                  <circle
                    r={22}
                    fill="#ffffff"
                    stroke={COLORS.accent}
                    strokeWidth={2.5}
                  />
                  <circle
                    r={22}
                    fill={COLORS.accent}
                    opacity={0.1}
                  />
                  <text
                    textAnchor="middle"
                    dy={5}
                    fontSize={12}
                    fontWeight={800}
                    fontFamily={FONTS.body}
                    fill={COLORS.textDark}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </AbsoluteFill>
  );
};
