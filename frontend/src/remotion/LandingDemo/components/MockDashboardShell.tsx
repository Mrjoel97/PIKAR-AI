import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { COLORS } from '../constants';
import { type AgentInfo } from '../data/personas';
import { AgentBadge } from './AgentBadge';
import { PersonaAvatar } from './PersonaAvatar';

interface MockDashboardShellProps {
  personaTitle: string;
  personaEmoji: string;
  personaGradient: [string, string];
  agents: AgentInfo[];
  metrics?: { label: string; value: string; trend: 'up' | 'down' | 'flat' }[];
  children: React.ReactNode;
}

export const MockDashboardShell: React.FC<MockDashboardShellProps> = ({
  personaTitle, personaEmoji, personaGradient, agents, metrics, children,
}) => {
  const frame = useCurrentFrame();
  const shellOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex',
      backgroundColor: COLORS.bgDark, fontFamily: 'Inter, system-ui, sans-serif', opacity: shellOpacity,
    }}>
      {/* Sidebar */}
      <div style={{
        width: 280, backgroundColor: 'rgba(0,0,0,0.4)',
        borderRight: '1px solid rgba(255,255,255,0.06)', padding: 24,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {/* Logo */}
        <div style={{ fontSize: 22, fontWeight: 800, color: COLORS.accent, marginBottom: 24, letterSpacing: -0.5 }}>
          pikar<span style={{ color: COLORS.textPrimary }}>.</span>ai
        </div>

        {/* Persona header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <PersonaAvatar emoji={personaEmoji} gradient={personaGradient} size={44} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.textPrimary }}>{personaTitle}</div>
            <div style={{ fontSize: 11, color: COLORS.textMuted }}>Workspace</div>
          </div>
        </div>

        {/* Active agents */}
        <div style={{ fontSize: 11, fontWeight: 600, color: COLORS.textMuted, marginBottom: 8, textTransform: 'uppercase' as const, letterSpacing: 1 }}>
          Active Agents
        </div>
        {agents.map((agent, i) => (
          <AgentBadge key={agent.name} name={agent.name} emoji={agent.emoji} role={agent.role} appearFrame={15 + i * 12} />
        ))}

        {/* Metrics at bottom */}
        {metrics && (
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: COLORS.textMuted, textTransform: 'uppercase' as const, letterSpacing: 1, marginBottom: 4 }}>
              Live Metrics
            </div>
            {metrics.map((m) => (
              <div key={m.label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', borderRadius: 8, backgroundColor: 'rgba(255,255,255,0.03)',
              }}>
                <span style={{ fontSize: 12, color: COLORS.textSecondary }}>{m.label}</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: m.trend === 'up' ? '#22c55e' : m.trend === 'down' ? '#ef4444' : COLORS.textPrimary }}>
                  {m.value} {m.trend === 'up' ? '\u2191' : m.trend === 'down' ? '\u2193' : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{
          height: 56, borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', padding: '0 28px', justifyContent: 'space-between',
        }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: COLORS.textPrimary }}>{personaTitle} Dashboard</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#22c55e' }} />
            <span style={{ fontSize: 12, color: COLORS.textSecondary }}>All agents online</span>
          </div>
        </div>
        <div style={{ flex: 1, padding: 28, overflow: 'hidden' }}>{children}</div>
      </div>
    </div>
  );
};
