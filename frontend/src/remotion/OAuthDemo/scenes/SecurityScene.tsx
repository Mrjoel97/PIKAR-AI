import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS } from '../constants';

const SecurityPoint: React.FC<{
  icon: string;
  title: string;
  description: string;
  delay: number;
}> = ({ icon, title, description, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [delay, delay + fps * 0.4], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const x = interpolate(frame, [delay, delay + fps * 0.4], [30, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        display: 'flex',
        gap: 20,
        padding: '20px 24px',
        background: 'rgba(255,255,255,0.03)',
        borderRadius: 16,
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div style={{ fontSize: 32, flexShrink: 0, marginTop: 2 }}>{icon}</div>
      <div>
        <div
          style={{
            fontFamily: FONTS.display,
            fontSize: 20,
            fontWeight: 600,
            color: COLORS.textPrimary,
            marginBottom: 6,
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 16,
            color: COLORS.textSecondary,
            lineHeight: 1.5,
          }}
        >
          {description}
        </div>
      </div>
    </div>
  );
};

export const SecurityScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${COLORS.bgDark} 0%, #0d3333 100%)`,
        padding: 80,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          opacity: headerOpacity,
          fontFamily: FONTS.mono,
          fontSize: 14,
          color: COLORS.accent,
          letterSpacing: 3,
          textTransform: 'uppercase',
          marginBottom: 12,
        }}
      >
        Section 7 of 7
      </div>

      <div
        style={{
          opacity: headerOpacity,
          fontFamily: FONTS.display,
          fontSize: 48,
          fontWeight: 700,
          color: COLORS.textPrimary,
          marginBottom: 48,
        }}
      >
        Data Handling & Security
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 20,
        }}
      >
        <SecurityPoint
          icon="🔐"
          title="Encrypted Token Storage"
          description="OAuth tokens are stored securely in Supabase Auth. Access tokens and refresh tokens never touch client-side storage or local storage."
          delay={fps * 0.8}
        />
        <SecurityPoint
          icon="👤"
          title="User's Own Credentials"
          description="All Google API calls use the authenticated user's own OAuth credentials. No service account impersonation — the user is always in control."
          delay={fps * 1.4}
        />
        <SecurityPoint
          icon="🚫"
          title="No Persistent Email Storage"
          description="Email content is processed in real-time by AI agents. Only summaries and user-approved actions persist. Raw email content is never stored."
          delay={fps * 2.0}
        />
        <SecurityPoint
          icon="🔄"
          title="Revocable Access"
          description="Users can disconnect Pikar AI at any time via Settings or through Google Account security settings. Tokens are immediately invalidated."
          delay={fps * 2.6}
        />
        <SecurityPoint
          icon="✅"
          title="Approval Workflows"
          description="Sensitive actions like sending emails require explicit user confirmation. Agents draft content; users approve before execution."
          delay={fps * 3.2}
        />
        <SecurityPoint
          icon="🛡️"
          title="Minimal Scope Principle"
          description="We request only the scopes needed for core functionality. Each scope maps to a specific, demonstrated feature in the application."
          delay={fps * 3.8}
        />
      </div>
    </AbsoluteFill>
  );
};
