import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS } from '../constants';

// --- Helpers ---

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

const VOICE_TEXT = 'Prepare my morning briefing and flag anything urgent';

const METRICS = [
  { label: 'Revenue', value: '+12% MoM', arrow: '\u2191', color: '#16a34a' },
  { label: 'Burn Rate', value: '14 months', arrow: '\u2191', color: '#16a34a' },
  { label: 'Decisions Pending', value: '3', arrow: '\u2014', color: '#d97706' },
] as const;

export const BriefingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- Time badge (top-left) ---
  const badgeOpacity = interpolate(frame, [0, 20], [0, 1], CLAMP);

  // --- Agent badges (top-right) ---
  const agentBadge1Opacity = interpolate(frame, [10, 30], [0, 1], CLAMP);
  const agentBadge2Opacity = interpolate(frame, [20, 40], [0, 1], CLAMP);

  // --- Phase 1: Voice waveform + typed text (0-150) ---
  const waveformOpacity = interpolate(frame, [10, 30, 130, 150], [0, 1, 1, 0], CLAMP);
  const typedChars = Math.floor(
    interpolate(frame, [30, 130], [0, VOICE_TEXT.length], CLAMP),
  );

  // --- Phase 2: Briefing card slides up (150-350) ---
  const cardY = interpolate(frame, [150, 200], [600, 0], CLAMP);
  const cardOpacity = interpolate(frame, [150, 190], [0, 1], CLAMP);

  // --- Phase 3: Alert card slides in from right (350-480) ---
  const alertX = interpolate(frame, [350, 400], [500, 0], CLAMP);
  const alertOpacity = interpolate(frame, [350, 390], [0, 1], CLAMP);
  const alertGlow = interpolate(frame % 40, [0, 20, 40], [0.15, 0.35, 0.15]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#f8fafa',
        fontFamily: FONTS.body,
      }}
    >
      {/* Subtle grid pattern */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.025,
          backgroundImage: `linear-gradient(${COLORS.textDark} 1px, transparent 1px), linear-gradient(90deg, ${COLORS.textDark} 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
      />

      {/* Top-left: Time badge */}
      <div
        style={{
          position: 'absolute',
          top: 48,
          left: 64,
          opacity: badgeOpacity,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '14px 28px',
          borderRadius: 16,
          backgroundColor: 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(12px)',
          border: `1px solid ${COLORS.border}`,
          boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.08)',
        }}
      >
        <span style={{ fontSize: 28 }}>{'\u2600\uFE0F'}</span>
        <span
          style={{
            fontSize: 28,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
          }}
        >
          7:30 AM
        </span>
      </div>

      {/* Top-right: Agent badges */}
      <div
        style={{
          position: 'absolute',
          top: 48,
          right: 64,
          display: 'flex',
          gap: 14,
        }}
      >
        <div
          style={{
            opacity: agentBadge1Opacity,
            padding: '12px 22px',
            borderRadius: 14,
            backgroundColor: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(12px)',
            border: `1px solid ${COLORS.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.08)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 20 }}>{'\u{1F451}'}</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.textDark,
              fontFamily: FONTS.display,
            }}
          >
            Executive Agent
          </span>
        </div>
        <div
          style={{
            opacity: agentBadge2Opacity,
            padding: '12px 22px',
            borderRadius: 14,
            backgroundColor: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(12px)',
            border: `1px solid ${COLORS.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.08)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 20 }}>{'\u{1F4C8}'}</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.textDark,
              fontFamily: FONTS.display,
            }}
          >
            Data Agent
          </span>
        </div>
      </div>

      {/* ============ PHASE 1: Voice waveform + typed text ============ */}
      <div
        style={{
          position: 'absolute',
          top: 180,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: waveformOpacity,
        }}
      >
        {/* Waveform bars */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            height: 80,
            marginBottom: 32,
          }}
        >
          {Array.from({ length: 32 }).map((_, i) => {
            const barPhase = (frame * 3 + i * 11) % 60;
            const barHeight = interpolate(
              barPhase,
              [0, 15, 30, 45, 60],
              [12, 50, 20, 60, 12],
            );
            const barOpacity = interpolate(
              Math.abs(i - 16),
              [0, 16],
              [1, 0.3],
              CLAMP,
            );
            return (
              <div
                key={i}
                style={{
                  width: 6,
                  height: barHeight,
                  borderRadius: 3,
                  backgroundColor: COLORS.accent,
                  opacity: barOpacity,
                }}
              />
            );
          })}
        </div>

        {/* Typed text */}
        <div
          style={{
            fontSize: 32,
            fontWeight: 500,
            fontFamily: FONTS.body,
            color: COLORS.textDark,
            maxWidth: 900,
            textAlign: 'center',
            lineHeight: 1.4,
          }}
        >
          {'\u201C'}
          {VOICE_TEXT.slice(0, typedChars)}
          <span
            style={{
              opacity: frame % 30 < 20 ? 1 : 0,
              color: COLORS.accent,
              fontWeight: 700,
            }}
          >
            |
          </span>
          {'\u201D'}
        </div>
      </div>

      {/* ============ PHASE 2: Briefing card slides up ============ */}
      {frame >= 150 && (
        <div
          style={{
            position: 'absolute',
            top: 160,
            left: '50%',
            transform: `translateX(-50%) translateY(${cardY}px)`,
            opacity: cardOpacity,
            width: 720,
            backgroundColor: '#ffffff',
            borderRadius: 24,
            border: `1px solid ${COLORS.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Card header */}
          <div
            style={{
              padding: '28px 40px',
              borderBottom: `1px solid ${COLORS.border}`,
              background: 'linear-gradient(135deg, rgba(59,191,151,0.04), rgba(59,191,151,0.08))',
              display: 'flex',
              alignItems: 'center',
              gap: 14,
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal500})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ fontSize: 22 }}>{'\u{1F4CB}'}</span>
            </div>
            <span
              style={{
                fontSize: 28,
                fontWeight: 800,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
              }}
            >
              Morning Briefing
            </span>
            <span
              style={{
                marginLeft: 'auto',
                fontSize: 16,
                color: COLORS.textMuted,
                fontFamily: FONTS.mono,
              }}
            >
              Today
            </span>
          </div>

          {/* Metric rows */}
          <div style={{ padding: '12px 0' }}>
            {METRICS.map((metric, i) => {
              const rowDelay = 180 + i * 20;
              const rowOpacity = interpolate(
                frame,
                [rowDelay, rowDelay + 20],
                [0, 1],
                CLAMP,
              );
              const rowX = interpolate(
                frame,
                [rowDelay, rowDelay + 20],
                [-30, 0],
                CLAMP,
              );
              return (
                <div
                  key={metric.label}
                  style={{
                    padding: '22px 40px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: i % 2 === 0 ? 'rgba(0,0,0,0.015)' : 'transparent',
                    borderBottom:
                      i < METRICS.length - 1
                        ? `1px solid ${COLORS.border}`
                        : 'none',
                    opacity: rowOpacity,
                    transform: `translateX(${rowX}px)`,
                  }}
                >
                  <span
                    style={{
                      fontSize: 22,
                      fontWeight: 600,
                      color: COLORS.textDark,
                      fontFamily: FONTS.body,
                    }}
                  >
                    {metric.label}
                  </span>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '6px 14px',
                      borderRadius: 10,
                      backgroundColor: `${metric.color}14`,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 24,
                        fontWeight: 700,
                        fontFamily: FONTS.mono,
                        color: COLORS.textDark,
                      }}
                    >
                      {metric.value}
                    </span>
                    <span
                      style={{
                        fontSize: 22,
                        fontWeight: 700,
                        color: metric.color,
                      }}
                    >
                      {metric.arrow}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ============ PHASE 3: Alert card slides in from right ============ */}
      {frame >= 350 && (
        <div
          style={{
            position: 'absolute',
            bottom: 120,
            left: '50%',
            transform: `translateX(calc(-50% + ${alertX}px))`,
            opacity: alertOpacity,
            width: 700,
            background: 'linear-gradient(135deg, #ffffff, rgba(239, 68, 68, 0.03))',
            borderRadius: 20,
            border: `1px solid ${COLORS.border}`,
            boxShadow: `inset 0 1px 0 rgba(255,255,255,0.8), 0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.08), 0 0 60px rgba(234, 88, 12, ${alertGlow})`,
            overflow: 'hidden',
            display: 'flex',
          }}
        >
          {/* Red-orange left border */}
          <div
            style={{
              width: 8,
              flexShrink: 0,
              background: 'linear-gradient(180deg, #ef4444, #ea580c)',
            }}
          />

          <div style={{ padding: '28px 36px', flex: 1 }}>
            {/* Alert title */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                marginBottom: 12,
              }}
            >
              <span style={{ fontSize: 24 }}>{'\u26A0\uFE0F'}</span>
              <span
                style={{
                  fontSize: 24,
                  fontWeight: 800,
                  fontFamily: FONTS.display,
                  color: '#dc2626',
                }}
              >
                Anomaly Detected
              </span>
            </div>

            {/* Alert body */}
            <div
              style={{
                fontSize: 20,
                fontWeight: 500,
                color: COLORS.textDark,
                fontFamily: FONTS.body,
                lineHeight: 1.5,
              }}
            >
              APAC customer churn spiked{' '}
              <span style={{ fontWeight: 800, color: '#dc2626' }}>23%</span>{' '}
              {'\u2014'} Data Agent recommending deep-dive
            </div>

            {/* Subtle agent attribution */}
            <div
              style={{
                marginTop: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span style={{ fontSize: 16 }}>{'\u{1F4C8}'}</span>
              <span
                style={{
                  fontSize: 14,
                  color: COLORS.textMuted,
                  fontFamily: FONTS.mono,
                }}
              >
                Data Agent flagged 2 min ago
              </span>
            </div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
