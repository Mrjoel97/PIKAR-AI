import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS } from '../constants';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] as const;

// Calendar cell colors (representing different content types)
const CELL_COLORS = [
  ['#3b82f6', '#8b5cf6', '#ec4899', '#f97316', '#22c55e'],
  ['#ec4899', '#22c55e', '#3b82f6', '#8b5cf6', '#f97316'],
  ['#f97316', '#3b82f6', '#22c55e', '#ec4899', '#8b5cf6'],
] as const;

const PLATFORMS = [
  {
    name: 'Instagram',
    icon: '\u{1F4F7}',
    gradient: ['#ec4899', '#8b5cf6'],
    aspectLabel: '1:1',
    format: 'Square',
  },
  {
    name: 'Twitter / X',
    icon: '\u{1F426}',
    gradient: ['#3b82f6', '#60a5fa'],
    aspectLabel: '16:9',
    format: 'Landscape',
  },
  {
    name: 'LinkedIn',
    icon: '\u{1F4BC}',
    gradient: ['#2563eb', '#3b82f6'],
    aspectLabel: '1.91:1',
    format: 'Professional',
  },
] as const;

export const ContentScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- Time badge ---
  const badgeOpacity = interpolate(frame, [0, 20], [0, 1], CLAMP);

  // --- Agent badges ---
  const agentBadge1Opacity = interpolate(frame, [10, 30], [0, 1], CLAMP);
  const agentBadge2Opacity = interpolate(frame, [20, 40], [0, 1], CLAMP);

  // --- Phase 1: Calendar grid (0-140) ---
  const calendarOpacity = interpolate(frame, [15, 45], [0, 1], CLAMP);

  // --- Phase 3: Counter stats (300-420) ---

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#f8fafa',
        fontFamily: FONTS.body,
      }}
    >
      {/* Subtle grid */}
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
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        }}
      >
        <span style={{ fontSize: 28 }}>{'\u270F\uFE0F'}</span>
        <span
          style={{
            fontSize: 28,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
          }}
        >
          11:00 AM
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
            boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 20 }}>{'\u270D\uFE0F'}</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.textDark,
              fontFamily: FONTS.display,
            }}
          >
            Content Agent
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
            boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 20 }}>{'\u{1F4E3}'}</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.textDark,
              fontFamily: FONTS.display,
            }}
          >
            Marketing Agent
          </span>
        </div>
      </div>

      {/* ============ PHASE 1: Content Calendar Grid ============ */}
      <div
        style={{
          position: 'absolute',
          top: 150,
          left: '50%',
          transform: 'translateX(-50%)',
          opacity: calendarOpacity,
          width: 820,
        }}
      >
        {/* Calendar header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal500})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ fontSize: 20 }}>{'\u{1F4C5}'}</span>
          </div>
          <span
            style={{
              fontSize: 24,
              fontWeight: 800,
              fontFamily: FONTS.display,
              color: COLORS.textDark,
            }}
          >
            Content Calendar
          </span>
          <span
            style={{
              fontSize: 16,
              color: COLORS.textMuted,
              fontFamily: FONTS.mono,
              marginLeft: 8,
            }}
          >
            This Week
          </span>
        </div>

        {/* Calendar card */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: 20,
            border: `1px solid ${COLORS.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05), 0 20px 48px rgba(0,0,0,0.07)',
            overflow: 'hidden',
          }}
        >
          {/* Day headers */}
          <div
            style={{
              display: 'flex',
              borderBottom: `1px solid ${COLORS.border}`,
            }}
          >
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                style={{
                  flex: 1,
                  padding: '16px 0',
                  textAlign: 'center',
                  fontSize: 16,
                  fontWeight: 700,
                  fontFamily: FONTS.mono,
                  color: COLORS.textMuted,
                  borderRight:
                    day !== 'Fri' ? `1px solid ${COLORS.border}` : 'none',
                }}
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar rows */}
          {CELL_COLORS.map((row, rowIdx) => (
            <div
              key={rowIdx}
              style={{
                display: 'flex',
                borderBottom:
                  rowIdx < CELL_COLORS.length - 1
                    ? `1px solid ${COLORS.border}`
                    : 'none',
              }}
            >
              {row.map((color, colIdx) => {
                const cellIndex = rowIdx * 5 + colIdx;
                const cellDelay = 35 + cellIndex * 5;
                const cellOpacity = interpolate(
                  frame,
                  [cellDelay, cellDelay + 12],
                  [0, 1],
                  CLAMP,
                );
                const cellScale = spring({
                  frame: Math.max(0, frame - cellDelay),
                  fps,
                  config: { damping: 14, stiffness: 150 },
                });

                return (
                  <div
                    key={colIdx}
                    style={{
                      flex: 1,
                      padding: '20px 0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRight:
                        colIdx < 4 ? `1px solid ${COLORS.border}` : 'none',
                    }}
                  >
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: 12,
                        backgroundColor: color,
                        opacity: cellOpacity,
                        transform: `scale(${cellScale})`,
                        boxShadow: `0 2px 8px ${color}30, 0 4px 16px ${color}20`,
                      }}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* ============ PHASE 2: Platform preview cards ============ */}
      {frame >= 140 && (
        <div
          style={{
            position: 'absolute',
            bottom: 180,
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            gap: 32,
          }}
        >
          {PLATFORMS.map((platform, i) => {
            const cardDelay = 150 + i * 25;
            const cardY = interpolate(
              frame,
              [cardDelay, cardDelay + 30],
              [80, 0],
              CLAMP,
            );
            const cardOpacity = interpolate(
              frame,
              [cardDelay, cardDelay + 25],
              [0, 1],
              CLAMP,
            );

            return (
              <div
                key={platform.name}
                style={{
                  width: 260,
                  background: 'linear-gradient(180deg, #ffffff, #fafafa)',
                  borderRadius: 20,
                  border: `1px solid ${COLORS.border}`,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04), 0 8px 28px rgba(0,0,0,0.08)',
                  overflow: 'hidden',
                  opacity: cardOpacity,
                  transform: `translateY(${cardY}px)`,
                }}
              >
                {/* Platform color bar */}
                <div
                  style={{
                    height: 8,
                    background: `linear-gradient(90deg, ${platform.gradient[0]}, ${platform.gradient[1]})`,
                  }}
                />

                {/* Card content */}
                <div style={{ padding: '20px 22px' }}>
                  {/* Platform name + icon */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 16,
                    }}
                  >
                    <span style={{ fontSize: 20 }}>{platform.icon}</span>
                    <span
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        fontFamily: FONTS.display,
                        color: COLORS.textDark,
                      }}
                    >
                      {platform.name}
                    </span>
                  </div>

                  {/* Image placeholder */}
                  <div
                    style={{
                      width: '100%',
                      height: platform.name === 'Instagram' ? 140 : 100,
                      borderRadius: 12,
                      background: `linear-gradient(135deg, ${platform.gradient[0]}20, ${platform.gradient[1]}20)`,
                      border: `1px dashed ${platform.gradient[0]}60`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: 14,
                    }}
                  >
                    <div
                      style={{
                        padding: '8px 16px',
                        borderRadius: 8,
                        backgroundColor: `${platform.gradient[0]}18`,
                        backdropFilter: 'blur(4px)',
                      }}
                    >
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color: platform.gradient[0],
                          fontFamily: FONTS.mono,
                        }}
                      >
                        AI Generated
                      </span>
                    </div>
                  </div>

                  {/* Scheduled badge */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span
                      style={{
                        fontSize: 12,
                        color: COLORS.textMuted,
                        fontFamily: FONTS.mono,
                      }}
                    >
                      {platform.format}
                    </span>
                    <div
                      style={{
                        padding: '4px 12px',
                        borderRadius: 8,
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                      }}
                    >
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 800,
                          color: '#16a34a',
                          fontFamily: FONTS.mono,
                        }}
                      >
                        Scheduled
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ============ PHASE 3: Animated counters ============ */}
      {frame >= 300 && (() => {
        const statsOpacity = interpolate(frame, [300, 330], [0, 1], CLAMP);
        const statsScale = spring({
          frame: Math.max(0, frame - 300),
          fps,
          config: { damping: 12, stiffness: 80 },
        });

        const postsCount = Math.floor(
          interpolate(frame, [310, 380], [0, 30], CLAMP),
        );
        const platformsCount = Math.floor(
          interpolate(frame, [320, 370], [0, 5], CLAMP),
        );

        const STATS = [
          { value: `${postsCount}`, label: 'posts generated', color: COLORS.accent },
          { value: `${platformsCount}`, label: 'platforms', color: '#3b82f6' },
          { value: '1', label: 'command', color: '#8b5cf6' },
        ];

        return (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(248, 250, 250, 0.92)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 80,
              opacity: statsOpacity,
              transform: `scale(${statsScale})`,
            }}
          >
            {STATS.map((stat, i) => {
              const statDelay = 305 + i * 12;
              const statOpacity = interpolate(
                frame,
                [statDelay, statDelay + 20],
                [0, 1],
                CLAMP,
              );
              return (
                <div
                  key={stat.label}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 12,
                    opacity: statOpacity,
                    padding: '36px 48px',
                    borderRadius: 24,
                    backgroundColor: 'rgba(255,255,255,0.7)',
                    backdropFilter: 'blur(8px)',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
                  }}
                >
                  <span
                    style={{
                      fontSize: 96,
                      fontWeight: 900,
                      fontFamily: FONTS.display,
                      color: stat.color,
                      lineHeight: 1,
                      textShadow: `0 2px 12px ${stat.color}30`,
                    }}
                  >
                    {stat.value}
                  </span>
                  <span
                    style={{
                      fontSize: 26,
                      fontWeight: 600,
                      fontFamily: FONTS.body,
                      color: COLORS.textDark,
                    }}
                  >
                    {stat.label}
                  </span>
                </div>
              );
            })}
          </div>
        );
      })()}
    </AbsoluteFill>
  );
};
