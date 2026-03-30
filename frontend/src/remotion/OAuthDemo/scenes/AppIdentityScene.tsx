import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  staticFile,
} from 'remotion';
import { COLORS, FONTS, TOTAL_SECTIONS } from '../constants';

const InfoRow: React.FC<{
  label: string;
  value: string;
  delay: number;
  mono?: boolean;
}> = ({ label, value, delay, mono }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [delay, delay + fps * 0.4], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const x = interpolate(frame, [delay, delay + fps * 0.4], [40, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        display: 'flex',
        alignItems: 'baseline',
        gap: 16,
        marginBottom: 20,
      }}
    >
      <span
        style={{
          fontFamily: FONTS.body,
          fontSize: 20,
          color: COLORS.textMuted,
          minWidth: 200,
          textAlign: 'right',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: mono ? FONTS.mono : FONTS.body,
          fontSize: mono ? 18 : 22,
          color: COLORS.textPrimary,
          background: mono ? 'rgba(255,255,255,0.06)' : 'transparent',
          padding: mono ? '4px 12px' : 0,
          borderRadius: mono ? 8 : 0,
        }}
      >
        {value}
      </span>
    </div>
  );
};

export const AppIdentityScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const screenshotOpacity = interpolate(frame, [fps * 4, fps * 5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const sectionBadgeOpacity = interpolate(frame, [0, fps * 0.3], [0, 1], {
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
      {/* Section badge */}
      <div
        style={{
          opacity: sectionBadgeOpacity,
          fontFamily: FONTS.mono,
          fontSize: 14,
          color: COLORS.accent,
          letterSpacing: 3,
          textTransform: 'uppercase',
          marginBottom: 12,
        }}
      >
        Section 1 of {TOTAL_SECTIONS}
      </div>

      {/* Header */}
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
        App Identity & OAuth Client
      </div>

      {/* Info rows */}
      <div style={{ display: 'flex', gap: 80 }}>
        <div style={{ flex: 1 }}>
          <InfoRow label="App Name" value="Pikar AI" delay={fps * 0.8} />
          <InfoRow
            label="OAuth Client ID"
            value="(shown in Google Cloud Console)"
            delay={fps * 1.2}
            mono
          />
          <InfoRow
            label="Redirect URI"
            value="https://your-domain.com/auth/callback"
            delay={fps * 1.6}
            mono
          />
          <InfoRow
            label="Auth Provider"
            value="Supabase Auth (Google OAuth)"
            delay={fps * 2.0}
          />
          <InfoRow
            label="Token Storage"
            value="Supabase Auth (encrypted, server-side)"
            delay={fps * 2.4}
          />
          <InfoRow
            label="Access Type"
            value="offline (refresh token for background access)"
            delay={fps * 2.8}
            mono
          />
        </div>

        {/* Login page screenshot */}
        <div
          style={{
            opacity: screenshotOpacity,
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              borderRadius: 16,
              overflow: 'hidden',
              boxShadow: '0 30px 80px rgba(0,0,0,0.5)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          >
            <Img
              src={staticFile('oauth-video-frames/01-login-page.png')}
              style={{ width: 700, height: 'auto' }}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
