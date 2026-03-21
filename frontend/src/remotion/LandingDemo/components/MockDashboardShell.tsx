import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';
import { type AgentInfo } from '../data/personas';
import { AgentBadge } from './AgentBadge';
import { PersonaAvatar } from './PersonaAvatar';

interface MockDashboardShellProps {
  personaTitle: string;
  personaEmoji: string;
  personaGradient: [string, string];
  personaBadgeColor: string;
  personaTextColor: string;
  agents: AgentInfo[];
  metrics?: { label: string; value: string; trend: 'up' | 'down' | 'flat' }[];
  children: React.ReactNode;
}

export const MockDashboardShell: React.FC<MockDashboardShellProps> = ({
  personaTitle, personaEmoji, personaGradient, personaBadgeColor, personaTextColor, agents, metrics, children,
}) => {
  const frame = useCurrentFrame();
  const shellOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

  // Navigation items matching real app sidebar
  const navItems = [
    { icon: '\u{1F4CB}', label: 'Command Center', active: true },
    { icon: '\u{1F514}', label: 'Approvals' },
    { icon: '\u{1F4B3}', label: 'Finance' },
    { icon: '\u{1F4DD}', label: 'Content' },
    { icon: '\u{1F4C8}', label: 'Sales Pipeline' },
    { icon: '\u{1F6E1}\u{FE0F}', label: 'Compliance' },
  ];

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex',
      backgroundColor: COLORS.bgDark, fontFamily: FONTS.body, opacity: shellOpacity,
    }}>
      {/* Sidebar - matching real PremiumShell */}
      <div style={{
        width: 260, backgroundColor: 'rgba(0,0,0,0.3)',
        borderRight: `1px solid ${COLORS.borderDark}`, padding: 20,
        display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        {/* Logo - Brain icon + Pikar AI text */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(26, 138, 110, 0.3)',
          }}>
            <span style={{ fontSize: 18 }}>{'\u{1F9E0}'}</span>
          </div>
          <div style={{ fontFamily: FONTS.display, fontSize: 20, fontWeight: 700, color: COLORS.textPrimary }}>
            Pikar <span style={{ color: COLORS.primary }}>AI</span>
          </div>
        </div>

        {/* Persona badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20,
          padding: '10px 12px', borderRadius: 12,
          backgroundColor: 'rgba(255,255,255,0.04)',
        }}>
          <PersonaAvatar emoji={personaEmoji} gradient={personaGradient} size={38} />
          <div>
            <div style={{
              fontSize: 13, fontWeight: 600, color: COLORS.textPrimary,
              fontFamily: FONTS.body,
            }}>{personaTitle}</div>
            <div style={{
              fontSize: 10, fontWeight: 500, fontFamily: FONTS.mono,
              color: personaTextColor, backgroundColor: personaBadgeColor,
              padding: '2px 8px', borderRadius: 4, display: 'inline-block', marginTop: 2,
            }}>
              Workspace
            </div>
          </div>
        </div>

        {/* Navigation items */}
        <div style={{ fontSize: 10, fontWeight: 600, color: COLORS.textMuted, marginBottom: 8, textTransform: 'uppercase' as const, letterSpacing: 1.2, fontFamily: FONTS.mono }}>
          Navigation
        </div>
        {navItems.map((item) => (
          <div key={item.label} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 12px', borderRadius: 8,
            backgroundColor: item.active ? 'rgba(59, 191, 151, 0.1)' : 'transparent',
            borderLeft: item.active ? `3px solid ${COLORS.accent}` : '3px solid transparent',
          }}>
            <span style={{ fontSize: 14 }}>{item.icon}</span>
            <span style={{
              fontSize: 13, fontFamily: FONTS.body,
              color: item.active ? COLORS.accent : COLORS.textSecondary,
              fontWeight: item.active ? 600 : 400,
            }}>{item.label}</span>
          </div>
        ))}

        {/* Active Agents section */}
        <div style={{ fontSize: 10, fontWeight: 600, color: COLORS.textMuted, marginTop: 20, marginBottom: 8, textTransform: 'uppercase' as const, letterSpacing: 1.2, fontFamily: FONTS.mono }}>
          Active Agents
        </div>
        {agents.map((agent, i) => (
          <AgentBadge key={agent.name} name={agent.name} emoji={agent.emoji} role={agent.role} appearFrame={15 + i * 12} />
        ))}

        {/* Metrics at bottom */}
        {metrics && (
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: COLORS.textMuted, textTransform: 'uppercase' as const, letterSpacing: 1.2, marginBottom: 4, fontFamily: FONTS.mono }}>
              Live Metrics
            </div>
            {metrics.map((m) => (
              <div key={m.label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', borderRadius: 8,
                backgroundColor: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.04)',
              }}>
                <span style={{ fontSize: 11, color: COLORS.textSecondary, fontFamily: FONTS.body }}>{m.label}</span>
                <span style={{
                  fontSize: 13, fontWeight: 700, fontFamily: FONTS.mono,
                  color: m.trend === 'up' ? '#22c55e' : m.trend === 'down' ? '#ef4444' : COLORS.textPrimary,
                }}>
                  {m.value} {m.trend === 'up' ? '\u2191' : m.trend === 'down' ? '\u2193' : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main content area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header bar - matching real app */}
        <div style={{
          height: 56, borderBottom: `1px solid ${COLORS.borderDark}`,
          display: 'flex', alignItems: 'center', padding: '0 24px', justifyContent: 'space-between',
          backgroundColor: 'rgba(0,0,0,0.15)',
        }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: COLORS.textPrimary, fontFamily: FONTS.display }}>
            {personaTitle} Dashboard
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', backgroundColor: '#22c55e',
              boxShadow: '0 0 6px rgba(34, 197, 94, 0.5)',
            }} />
            <span style={{ fontSize: 12, color: COLORS.textSecondary, fontFamily: FONTS.mono }}>All agents online</span>
          </div>
        </div>
        <div style={{ flex: 1, padding: 24, overflow: 'hidden' }}>{children}</div>
      </div>
    </div>
  );
};
