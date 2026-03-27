// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { COLORS } from '../constants';

interface AgentNode {
  name: string;
  emoji: string;
  angle: number;
}

const AGENTS: AgentNode[] = [
  { name: 'Financial', emoji: '\u{1F4CA}', angle: 0 },
  { name: 'Content', emoji: '\u{270D}\u{FE0F}', angle: 36 },
  { name: 'Strategic', emoji: '\u{1F9ED}', angle: 72 },
  { name: 'Sales', emoji: '\u{1F4B0}', angle: 108 },
  { name: 'Marketing', emoji: '\u{1F4E3}', angle: 144 },
  { name: 'Operations', emoji: '\u{2699}\u{FE0F}', angle: 180 },
  { name: 'HR', emoji: '\u{1F465}', angle: 216 },
  { name: 'Compliance', emoji: '\u{1F6E1}\u{FE0F}', angle: 252 },
  { name: 'Support', emoji: '\u{1F4AC}', angle: 288 },
  { name: 'Data', emoji: '\u{1F4C8}', angle: 324 },
];

interface AgentOrchestrationProps {
  highlightIndex?: number;
  size?: number;
}

export const AgentOrchestration: React.FC<AgentOrchestrationProps> = ({ size = 320 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const radius = size / 2 - 30;
  const center = size / 2;
  const highlightIndex = Math.floor((frame / (fps * 2)) % AGENTS.length);

  return (
    <div style={{ width: size, height: size, position: 'relative' }}>
      {/* Center hub */}
      <div style={{
        position: 'absolute', left: center - 28, top: center - 28, width: 56, height: 56,
        borderRadius: '50%', background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accentDark})`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 0 24px rgba(59, 191, 151, 0.4)', zIndex: 2,
      }}>
        <span style={{ fontSize: 24 }}>{'\u{1F451}'}</span>
      </div>

      {/* Agent nodes */}
      {AGENTS.map((agent, i) => {
        const rad = (agent.angle * Math.PI) / 180;
        const x = center + radius * Math.cos(rad) - 20;
        const y = center + radius * Math.sin(rad) - 20;
        const isActive = i === highlightIndex;
        const nodeScale = spring({
          frame: isActive ? frame % (fps * 2) : 0,
          fps,
          config: { damping: 15, stiffness: 120 },
        });
        const lineOpacity = interpolate(
          isActive ? frame % 30 : 30, [0, 15, 30], [0.1, 0.6, 0.1], { extrapolateRight: 'clamp' },
        );

        return (
          <React.Fragment key={agent.name}>
            <svg style={{ position: 'absolute', top: 0, left: 0, width: size, height: size, zIndex: 1 }}>
              <line x1={center} y1={center} x2={x + 20} y2={y + 20}
                stroke={isActive ? COLORS.accent : 'rgba(255,255,255,0.1)'}
                strokeWidth={isActive ? 2 : 1} opacity={isActive ? lineOpacity : 0.3} />
            </svg>
            <div style={{
              position: 'absolute', left: x, top: y, width: 40, height: 40, borderRadius: '50%',
              backgroundColor: isActive ? COLORS.accent : COLORS.bgCard,
              border: `1px solid ${isActive ? COLORS.accent : 'rgba(255,255,255,0.1)'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transform: `scale(${isActive ? 1 + (nodeScale - 1) * 0.15 : 1})`,
              boxShadow: isActive ? '0 0 16px rgba(59, 191, 151, 0.5)' : 'none', zIndex: 3,
            }}>
              <span style={{ fontSize: 16 }}>{agent.emoji}</span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};
