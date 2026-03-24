import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS } from '../constants';

/* ── Revenue line chart data (normalised 0-1) ───────────── */
const REVENUE_POINTS = [0.22, 0.28, 0.25, 0.35, 0.42, 0.40, 0.52, 0.58, 0.55, 0.68, 0.75, 0.82];

/* ── Funnel data ────────────────────────────────────────── */
const FUNNEL = [
  { label: 'Visitors', value: '12.4K', pct: 1.0 },
  { label: 'Leads', value: '3.2K', pct: 0.65 },
  { label: 'Qualified', value: '890', pct: 0.38 },
  { label: 'Closed', value: '142', pct: 0.18 },
];

/* ── Ops statuses ───────────────────────────────────────── */
const OPS_ROWS = [
  { label: 'Supply Chain', color: '#22c55e', status: 'Green' },
  { label: 'Compliance', color: '#22c55e', status: 'Green' },
  { label: 'Hiring Pipeline', color: '#f59e0b', status: 'Amber' },
];

/* ── Card appearance delays ─────────────────────────────── */
const CARD_DELAYS = [20, 40, 65, 90];

export const DashboardScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* ── Background ───────────────────────────────────────── */
  const gradientAngle = interpolate(frame, [0, 360], [0, 20]);

  /* ── Badge fade ───────────────────────────────────────── */
  const badgeOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  /* ── Tagline at bottom ────────────────────────────────── */
  const taglineOpacity = interpolate(frame, [280, 310], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  /* ── Helper: card entrance ────────────────────────────── */
  const cardEntrance = (delay: number) => {
    const s = spring({
      frame: Math.max(0, frame - delay),
      fps,
      config: { damping: 14, stiffness: 80 },
    });
    return {
      opacity: s,
      transform: `translateY(${interpolate(s, [0, 1], [30, 0])}px) scale(${0.95 + 0.05 * s})`,
    };
  };

  /* ── Revenue chart SVG path ───────────────────────────── */
  const chartW = 340;
  const chartH = 130;
  const chartPad = 10;
  const pointSpacing = (chartW - chartPad * 2) / (REVENUE_POINTS.length - 1);
  // Reveal progress
  const revealProgress = interpolate(
    frame,
    [CARD_DELAYS[0] + 30, CARD_DELAYS[0] + 130],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  const visiblePoints = Math.ceil(revealProgress * REVENUE_POINTS.length);
  const pathPoints = REVENUE_POINTS.slice(0, visiblePoints).map((v, i) => {
    const x = chartPad + i * pointSpacing;
    const y = chartH - chartPad - v * (chartH - chartPad * 2);
    return `${i === 0 ? 'M' : 'L'}${x},${y}`;
  });
  const pathD = pathPoints.join(' ');

  /* ── Grid dims ────────────────────────────────────────── */
  const GRID_GAP = 28;
  const CARD_W = 420;
  const CARD_H = 260;
  const GRID_LEFT = (1920 - CARD_W * 2 - GRID_GAP) / 2;
  const GRID_TOP = 130;

  const cardStyle = (col: number, row: number, delay: number): React.CSSProperties => ({
    position: 'absolute',
    left: GRID_LEFT + col * (CARD_W + GRID_GAP),
    top: GRID_TOP + row * (CARD_H + GRID_GAP),
    width: CARD_W,
    height: CARD_H,
    borderRadius: 24,
    background: 'linear-gradient(180deg, #ffffff, #fafcfb)',
    boxShadow: '0 1px 3px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05), 0 20px 48px rgba(0,0,0,0.08)',
    border: `1.5px solid ${COLORS.border}`,
    borderTop: '1px solid rgba(255,255,255,0.9)',
    padding: '24px 28px',
    display: 'flex',
    flexDirection: 'column',
    ...cardEntrance(delay),
  });

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
          top: 200,
          left: 600,
          width: 700,
          height: 700,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(59,191,151,0.06) 0%, transparent 70%)',
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

      {/* ── Time badge ────────────────────────────────────── */}
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
        <span style={{ fontSize: 22 }}>{'\u{1F4CA}'}</span>
        <span
          style={{
            fontSize: 22,
            fontWeight: 700,
            fontFamily: FONTS.mono,
            color: COLORS.textDark,
          }}
        >
          5:00 PM
        </span>
      </div>

      {/* ── Agent badges (top-right) ──────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 36,
          right: 48,
          opacity: badgeOpacity,
          display: 'flex',
          gap: 12,
        }}
      >
        {[
          { label: 'Financial Agent', emoji: '\u{1F4CA}' },
          { label: 'Sales Agent', emoji: '\u{1F4B0}' },
        ].map((b) => (
          <div
            key={b.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 18px',
              borderRadius: 14,
              backgroundColor: 'rgba(255,255,255,0.85)',
              boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <span
              style={{
                fontSize: 18,
                fontWeight: 700,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
              }}
            >
              {b.label}
            </span>
            <span style={{ fontSize: 20 }}>{b.emoji}</span>
          </div>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════════
          CARD 1 — Revenue Trend (top-left)
          ═══════════════════════════════════════════════════════ */}
      <div style={cardStyle(0, 0, CARD_DELAYS[0])}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 8,
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
            Revenue Trend
          </span>
          <span
            style={{
              fontSize: 20,
              fontWeight: 700,
              fontFamily: FONTS.mono,
              color: '#16a34a',
            }}
          >
            +12% MoM
          </span>
        </div>
        <svg
          width={chartW}
          height={chartH}
          viewBox={`0 0 ${chartW} ${chartH}`}
          style={{ marginTop: 8 }}
        >
          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map((v) => {
            const y = chartH - chartPad - v * (chartH - chartPad * 2);
            return (
              <line
                key={v}
                x1={chartPad}
                y1={y}
                x2={chartW - chartPad}
                y2={y}
                stroke={COLORS.border}
                strokeWidth={1}
                opacity={0.5}
              />
            );
          })}
          {/* Area fill */}
          {visiblePoints > 1 && (
            <path
              d={`${pathD} L${chartPad + (visiblePoints - 1) * pointSpacing},${chartH - chartPad} L${chartPad},${chartH - chartPad} Z`}
              fill="url(#revenueGrad)"
              opacity={0.15}
            />
          )}
          {/* Line */}
          {visiblePoints > 1 && (
            <path
              d={pathD}
              fill="none"
              stroke="#16a34a"
              strokeWidth={3.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
          {/* End dot */}
          {visiblePoints > 0 && (() => {
            const lastI = visiblePoints - 1;
            const cx = chartPad + lastI * pointSpacing;
            const cy =
              chartH - chartPad - REVENUE_POINTS[lastI] * (chartH - chartPad * 2);
            return (
              <>
                <circle cx={cx} cy={cy} r={7} fill="#ffffff" stroke="#16a34a" strokeWidth={3} />
                <circle cx={cx} cy={cy} r={3} fill="#16a34a" />
              </>
            );
          })()}
          <defs>
            <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#16a34a" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
            </linearGradient>
          </defs>
        </svg>
        <span
          style={{
            fontSize: 14,
            fontFamily: FONTS.body,
            color: COLORS.textMuted,
            marginTop: 6,
          }}
        >
          Revenue
        </span>
      </div>

      {/* ═══════════════════════════════════════════════════════
          CARD 2 — Conversion Funnel (top-right)
          ═══════════════════════════════════════════════════════ */}
      <div style={cardStyle(1, 0, CARD_DELAYS[1])}>
        <span
          style={{
            fontSize: 20,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
            marginBottom: 16,
          }}
        >
          Conversion Funnel
        </span>
        {FUNNEL.map((row, i) => {
          const barDelay = CARD_DELAYS[1] + 40 + i * 20;
          const barWidth = interpolate(
            frame,
            [barDelay, barDelay + 40],
            [0, row.pct * 100],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          // Gradient from blue to teal
          const barColor = interpolate(
            i,
            [0, FUNNEL.length - 1],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const colorStr =
            barColor < 0.5
              ? `rgb(59, 130, 246)` // blue
              : COLORS.accent; // teal
          return (
            <div
              key={row.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 10,
              }}
            >
              <span
                style={{
                  width: 80,
                  fontSize: 15,
                  fontWeight: 600,
                  fontFamily: FONTS.body,
                  color: COLORS.textDark,
                  textAlign: 'right',
                  flexShrink: 0,
                }}
              >
                {row.label}
              </span>
              <div
                style={{
                  flex: 1,
                  height: 32,
                  borderRadius: 10,
                  backgroundColor: 'rgba(0,0,0,0.04)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${barWidth}%`,
                    height: '100%',
                    borderRadius: 10,
                    background:
                      i === 0
                        ? 'linear-gradient(90deg, #3b82f6, #60a5fa)'
                        : i === 1
                          ? 'linear-gradient(90deg, #3b9eda, #56ccaa)'
                          : i === 2
                            ? `linear-gradient(90deg, #45c4a0, ${COLORS.accent})`
                            : `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.accentDark})`,
                  }}
                />
              </div>
              <span
                style={{
                  width: 50,
                  fontSize: 15,
                  fontWeight: 700,
                  fontFamily: FONTS.mono,
                  color: colorStr,
                  flexShrink: 0,
                }}
              >
                {row.value}
              </span>
            </div>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════════
          CARD 3 — Team Health (bottom-left)
          ═══════════════════════════════════════════════════════ */}
      <div
        style={{
          ...cardStyle(0, 1, CARD_DELAYS[2]),
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Circular gauge */}
        {(() => {
          const gaugeR = 70;
          const strokeW = 14;
          const circumference = 2 * Math.PI * gaugeR;
          const targetPct = 0.87;
          const fillDelay = CARD_DELAYS[2] + 30;
          const fillProgress = interpolate(
            frame,
            [fillDelay, fillDelay + 70],
            [0, targetPct],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const displayPct = Math.round(fillProgress * 100);
          return (
            <div style={{ position: 'relative', width: gaugeR * 2 + strokeW, height: gaugeR * 2 + strokeW }}>
              <svg
                width={gaugeR * 2 + strokeW}
                height={gaugeR * 2 + strokeW}
                viewBox={`0 0 ${gaugeR * 2 + strokeW} ${gaugeR * 2 + strokeW}`}
              >
                {/* Background ring */}
                <circle
                  cx={gaugeR + strokeW / 2}
                  cy={gaugeR + strokeW / 2}
                  r={gaugeR}
                  fill="none"
                  stroke="rgba(0,0,0,0.06)"
                  strokeWidth={strokeW}
                />
                {/* Glow behind filled ring */}
                <circle
                  cx={gaugeR + strokeW / 2}
                  cy={gaugeR + strokeW / 2}
                  r={gaugeR}
                  fill="none"
                  stroke="#16a34a"
                  strokeWidth={18}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference * (1 - fillProgress)}
                  transform={`rotate(-90 ${gaugeR + strokeW / 2} ${gaugeR + strokeW / 2})`}
                  opacity={0.15}
                  filter="blur(4px)"
                />
                {/* Filled ring */}
                <circle
                  cx={gaugeR + strokeW / 2}
                  cy={gaugeR + strokeW / 2}
                  r={gaugeR}
                  fill="none"
                  stroke="#16a34a"
                  strokeWidth={strokeW}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference * (1 - fillProgress)}
                  transform={`rotate(-90 ${gaugeR + strokeW / 2} ${gaugeR + strokeW / 2})`}
                />
              </svg>
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <span
                  style={{
                    fontSize: 48,
                    fontWeight: 900,
                    fontFamily: FONTS.display,
                    color: COLORS.textDark,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {displayPct}%
                </span>
              </div>
            </div>
          );
        })()}
        <span
          style={{
            fontSize: 16,
            fontWeight: 600,
            fontFamily: FONTS.body,
            color: COLORS.textMuted,
            marginTop: 10,
          }}
        >
          Team Satisfaction
        </span>
      </div>

      {/* ═══════════════════════════════════════════════════════
          CARD 4 — Ops Status (bottom-right)
          ═══════════════════════════════════════════════════════ */}
      <div style={cardStyle(1, 1, CARD_DELAYS[3])}>
        <span
          style={{
            fontSize: 20,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
            marginBottom: 20,
          }}
        >
          Ops Status
        </span>
        {OPS_ROWS.map((row, i) => {
          const rowDelay = CARD_DELAYS[3] + 40 + i * 25;
          const rowOpacity = interpolate(
            frame,
            [rowDelay, rowDelay + 20],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          // Pulsing dot
          const dotScale = interpolate(
            (frame + i * 15) % 50,
            [0, 25, 50],
            [1, 1.35, 1],
            { extrapolateRight: 'clamp' },
          );
          return (
            <div
              key={row.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                marginBottom: 18,
                opacity: rowOpacity,
                backgroundColor: i % 2 === 1 ? 'rgba(0,0,0,0.015)' : 'transparent',
                borderRadius: 8,
                padding: '4px 8px',
                margin: '0 -8px 18px -8px',
              }}
            >
              <div
                style={{
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  backgroundColor: row.color,
                  boxShadow: `0 0 8px ${row.color}80`,
                  transform: `scale(${dotScale})`,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 600,
                  fontFamily: FONTS.body,
                  color: COLORS.textDark,
                  flex: 1,
                }}
              >
                {row.label}
              </span>
              <span
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  fontFamily: FONTS.mono,
                  color: row.color,
                }}
              >
                {row.status}
              </span>
            </div>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════════
          TAGLINE
          ═══════════════════════════════════════════════════════ */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: taglineOpacity,
        }}
      >
        <span
          style={{
            display: 'inline-flex',
            padding: '16px 48px',
            borderRadius: 20,
            backgroundColor: 'rgba(255,255,255,0.6)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span
            style={{
              fontSize: 36,
              fontWeight: 800,
              fontFamily: FONTS.display,
              color: COLORS.textDark,
              letterSpacing: -0.5,
            }}
          >
            All 10 agents. One platform. Total command.
          </span>
        </span>
      </div>
    </AbsoluteFill>
  );
};
