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

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

const DAG_NODES = [
  { label: 'Request', emoji: '\u{1F4E9}' },
  { label: 'Review', emoji: '\u{1F50D}' },
  { label: 'Approve', emoji: '\u2705' },
  { label: 'Execute', emoji: '\u26A1' },
  { label: 'Complete', emoji: '\u{1F3C1}' },
] as const;

const NODE_SPACING = 280;
const DAG_START_X = 230;
const DAG_Y = 320;
const NODE_RADIUS = 42;

export const WorkflowScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- Time badge ---
  const badgeOpacity = interpolate(frame, [0, 20], [0, 1], CLAMP);

  // --- Agent badges ---
  const agentBadge1Opacity = interpolate(frame, [10, 30], [0, 1], CLAMP);
  const agentBadge2Opacity = interpolate(frame, [20, 40], [0, 1], CLAMP);

  // --- Phase 1: DAG nodes light up sequentially (0-180) ---
  const nodeActivationFrames = DAG_NODES.map((_, i) => 30 + i * 28);

  // --- Phase 2: Approval card (180-300) ---
  const approvalCardOpacity = interpolate(frame, [180, 220], [0, 1], CLAMP);
  const approvalCardScale = spring({
    frame: Math.max(0, frame - 180),
    fps,
    config: { damping: 14, stiffness: 80 },
  });

  // --- Phase 3: Checkmark + compliance (300-420) ---
  const checkmarkSpring = spring({
    frame: Math.max(0, frame - 310),
    fps,
    config: { damping: 10, stiffness: 100 },
  });
  const complianceSlideY = interpolate(frame, [340, 380], [40, 0], CLAMP);
  const complianceOpacity = interpolate(frame, [340, 380], [0, 1], CLAMP);

  // After phase 3, the Approve node turns green
  const approveNodeGreen = frame >= 310;

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
        <span style={{ fontSize: 28 }}>{'\u2699\uFE0F'}</span>
        <span
          style={{
            fontSize: 28,
            fontWeight: 700,
            fontFamily: FONTS.display,
            color: COLORS.textDark,
          }}
        >
          9:15 AM
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
          <span style={{ fontSize: 20 }}>{'\u2699\uFE0F'}</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.textDark,
              fontFamily: FONTS.display,
            }}
          >
            Operations Agent
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
          <span style={{ fontSize: 20 }}>{'\u{1F6E1}\uFE0F'}</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.textDark,
              fontFamily: FONTS.display,
            }}
          >
            Compliance Agent
          </span>
        </div>
      </div>

      {/* ============ PHASE 1: Workflow DAG ============ */}
      <div
        style={{
          position: 'absolute',
          top: DAG_Y - 60,
          left: 0,
          right: 0,
          height: 200,
        }}
      >
        {/* Connecting lines */}
        {DAG_NODES.slice(0, -1).map((_, i) => {
          const lineProgress = interpolate(
            frame,
            [nodeActivationFrames[i] + 10, nodeActivationFrames[i + 1]],
            [0, 1],
            CLAMP,
          );
          const lineActive = frame >= nodeActivationFrames[i];
          const x1 = DAG_START_X + i * NODE_SPACING + NODE_RADIUS;
          const x2 = DAG_START_X + (i + 1) * NODE_SPACING - NODE_RADIUS;
          const lineWidth = (x2 - x1) * lineProgress;

          return (
            <div
              key={`line-${i}`}
              style={{
                position: 'absolute',
                top: 60 - 2,
                left: x1,
                width: lineWidth,
                height: 4,
                borderRadius: 2,
                backgroundColor: lineActive ? COLORS.accent : COLORS.border,
                opacity: lineActive ? 1 : 0.3,
              }}
            />
          );
        })}

        {/* Nodes */}
        {DAG_NODES.map((node, i) => {
          const nodeActive = frame >= nodeActivationFrames[i];
          const nodeSpring = spring({
            frame: Math.max(0, frame - nodeActivationFrames[i]),
            fps,
            config: { damping: 12, stiffness: 120 },
          });
          const isApproveNode = node.label === 'Approve';
          const nodeGreen = isApproveNode && approveNodeGreen;

          let bgColor: string;
          let bgGradient: string | undefined;
          if (nodeGreen) {
            bgColor = '#16a34a';
            bgGradient = 'linear-gradient(135deg, #22c55e, #16a34a)';
          } else if (nodeActive) {
            bgColor = COLORS.accent;
            bgGradient = `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accentDark})`;
          } else {
            bgColor = '#e2e8f0';
            bgGradient = undefined;
          }

          let borderColor: string;
          if (nodeGreen) {
            borderColor = '#16a34a';
          } else if (nodeActive) {
            borderColor = 'rgba(255,255,255,0.6)';
          } else {
            borderColor = COLORS.border;
          }

          return (
            <div
              key={node.label}
              style={{
                position: 'absolute',
                left: DAG_START_X + i * NODE_SPACING - NODE_RADIUS,
                top: 60 - NODE_RADIUS,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 14,
              }}
            >
              <div
                style={{
                  width: NODE_RADIUS * 2,
                  height: NODE_RADIUS * 2,
                  borderRadius: '50%',
                  backgroundColor: bgColor,
                  background: bgGradient || bgColor,
                  border: `3px solid ${borderColor}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transform: `scale(${nodeActive ? nodeSpring : 0.8})`,
                  boxShadow: nodeActive
                    ? '0 4px 12px rgba(59, 191, 151, 0.15), 0 8px 28px rgba(59, 191, 151, 0.2), inset 0 1px 2px rgba(255,255,255,0.5)'
                    : 'none',
                }}
              >
                <span
                  style={{
                    fontSize: 28,
                    filter: nodeActive ? 'none' : 'grayscale(100%)',
                    opacity: nodeActive ? 1 : 0.4,
                  }}
                >
                  {node.emoji}
                </span>
              </div>
              <span
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  fontFamily: FONTS.display,
                  color: nodeActive ? COLORS.textDark : COLORS.textMuted,
                }}
              >
                {node.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* ============ PHASE 2: Approval card ============ */}
      {frame >= 180 && (
        <div
          style={{
            position: 'absolute',
            top: 500,
            left: '50%',
            transform: `translateX(-50%) scale(${approvalCardScale})`,
            opacity: approvalCardOpacity,
            display: 'flex',
            gap: 40,
            alignItems: 'flex-start',
          }}
        >
          {/* Approval details card */}
          <div
            style={{
              width: 440,
              backgroundColor: '#ffffff',
              borderRadius: 24,
              border: `1px solid ${COLORS.border}`,
              borderTop: `3px solid ${COLORS.accent}`,
              boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.08)',
              padding: '32px 36px',
            }}
          >
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                fontFamily: FONTS.mono,
                color: COLORS.accent,
                textTransform: 'uppercase',
                letterSpacing: 1.5,
                marginBottom: 10,
              }}
            >
              Pending Approval
            </div>
            <div
              style={{
                fontSize: 28,
                fontWeight: 800,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
                marginBottom: 8,
              }}
            >
              Vendor Payment {'\u2014'} $45,000
            </div>
            <div
              style={{
                fontSize: 18,
                color: COLORS.textMuted,
                fontFamily: FONTS.body,
              }}
            >
              Requires VP sign-off
            </div>
          </div>

          {/* Phone mockup */}
          <div
            style={{
              width: 260,
              height: 340,
              borderRadius: 32,
              border: '2px solid #1a1a2e',
              backgroundColor: '#ffffff',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 20,
              padding: '24px 20px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.08), 0 16px 48px rgba(0,0,0,0.12), inset 0 1px 3px rgba(0,0,0,0.06)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Notch */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                width: 100,
                height: 24,
                borderRadius: '0 0 16px 16px',
                backgroundColor: COLORS.textDark,
              }}
            />

            <span
              style={{
                fontSize: 16,
                fontWeight: 600,
                fontFamily: FONTS.mono,
                color: COLORS.textMuted,
                marginTop: 20,
              }}
            >
              Magic Link Approval
            </span>

            <div
              style={{
                fontSize: 22,
                fontWeight: 700,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
                textAlign: 'center',
              }}
            >
              $45,000
            </div>

            <span
              style={{
                fontSize: 14,
                color: COLORS.textMuted,
                fontFamily: FONTS.body,
              }}
            >
              Vendor Payment
            </span>

            {/* Approve button */}
            <div
              style={{
                padding: '18px 56px',
                borderRadius: 16,
                background: `linear-gradient(135deg, #22c55e, #16a34a)`,
                boxShadow: '0 4px 16px rgba(34, 197, 94, 0.3)',
              }}
            >
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  color: '#ffffff',
                  fontFamily: FONTS.display,
                }}
              >
                {'\u2713'} Approve
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ============ PHASE 3: Green checkmark + compliance badge ============ */}
      {frame >= 310 && (
        <>
          {/* Big green checkmark overlay */}
          <div
            style={{
              position: 'absolute',
              top: 480,
              left: '50%',
              transform: `translate(-50%, -50%) scale(${checkmarkSpring})`,
              width: 120,
              height: 120,
              borderRadius: '50%',
              background: 'radial-gradient(circle at 30% 30%, #22c55e, #16a34a)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 16px rgba(22, 163, 74, 0.3), 0 12px 40px rgba(22, 163, 74, 0.4)',
              zIndex: 10,
            }}
          >
            <span
              style={{
                fontSize: 60,
                color: '#ffffff',
                fontWeight: 900,
                lineHeight: 1,
              }}
            >
              {'\u2713'}
            </span>
          </div>

          {/* Compliance badge */}
          <div
            style={{
              position: 'absolute',
              bottom: 80,
              left: '50%',
              transform: `translateX(-50%) translateY(${complianceSlideY}px)`,
              opacity: complianceOpacity,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '18px 36px',
              borderRadius: 18,
              backgroundColor: 'rgba(255,255,255,0.9)',
              backdropFilter: 'blur(12px)',
              border: `1px solid ${COLORS.border}`,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.08)',
            }}
          >
            <span style={{ fontSize: 28 }}>{'\u{1F6E1}\uFE0F'}</span>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                fontFamily: FONTS.display,
                color: COLORS.textDark,
              }}
            >
              SOC2 evidence auto-attached
            </span>
            <div
              style={{
                marginLeft: 12,
                padding: '6px 16px',
                borderRadius: 10,
                backgroundColor: 'rgba(22, 163, 74, 0.1)',
              }}
            >
              <span
                style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: '#16a34a',
                  fontFamily: FONTS.mono,
                }}
              >
                Verified
              </span>
            </div>
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};
