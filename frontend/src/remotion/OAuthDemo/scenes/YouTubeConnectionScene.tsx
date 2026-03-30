import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS, TOTAL_SECTIONS } from '../constants';

/**
 * Demonstrates the separate YouTube OAuth flow via Settings -> Social Accounts.
 * This is architecturally distinct from the main sign-in OAuth — it uses
 * SocialConnector with its own PKCE flow and separate consent screen.
 */

const FlowStep: React.FC<{
  step: number;
  label: string;
  sublabel: string;
  icon: string;
  delay: number;
  highlight?: boolean;
}> = ({ step, label, sublabel, icon, delay, highlight }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [delay, delay + fps * 0.4], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const scale = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '16px 20px',
        background: highlight
          ? 'rgba(43,168,143,0.12)'
          : 'rgba(255,255,255,0.03)',
        borderRadius: 14,
        border: `1px solid ${highlight ? 'rgba(43,168,143,0.3)' : 'rgba(255,255,255,0.06)'}`,
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 10,
          background: highlight
            ? `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.teal600})`
            : 'rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 20,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 16,
            fontWeight: 600,
            color: COLORS.textPrimary,
            marginBottom: 2,
          }}
        >
          {step}. {label}
        </div>
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 13,
            color: COLORS.textMuted,
          }}
        >
          {sublabel}
        </div>
      </div>
    </div>
  );
};

const PlatformCard: React.FC<{
  name: string;
  icon: string;
  connected: boolean;
  delay: number;
  highlight?: boolean;
}> = ({ name, icon, connected, delay, highlight }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [delay, delay + fps * 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        opacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 18px',
        background: highlight
          ? 'rgba(43,168,143,0.08)'
          : 'rgba(255,255,255,0.02)',
        borderRadius: 12,
        border: `1px solid ${highlight ? 'rgba(43,168,143,0.25)' : 'rgba(255,255,255,0.05)'}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 22 }}>{icon}</span>
        <span
          style={{
            fontFamily: FONTS.body,
            fontSize: 16,
            color: COLORS.textPrimary,
            fontWeight: 500,
          }}
        >
          {name}
        </span>
      </div>
      <div
        style={{
          fontFamily: FONTS.mono,
          fontSize: 11,
          fontWeight: 700,
          padding: '4px 12px',
          borderRadius: 6,
          letterSpacing: 1,
          textTransform: 'uppercase',
          ...(connected
            ? {
                background: COLORS.scopeBasicBg,
                color: '#166534',
              }
            : {
                background: 'rgba(255,255,255,0.06)',
                color: COLORS.textMuted,
              }),
        }}
      >
        {connected ? 'Connected' : 'Connect'}
      </div>
    </div>
  );
};

export const YouTubeConnectionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, fps * 0.4], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Animate the YouTube card from "Connect" to "Connected"
  const connectTransition = interpolate(
    frame,
    [fps * 7, fps * 7.5],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  const youtubeConnected = connectTransition > 0.5;

  // Show "separate flow" callout
  const calloutOpacity = interpolate(frame, [fps * 8, fps * 9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${COLORS.bgDark} 0%, #0d3333 100%)`,
        padding: 80,
        display: 'flex',
        gap: 60,
      }}
    >
      {/* Left: Title + Social Accounts mock */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Section badge */}
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
          Section 7 of {TOTAL_SECTIONS}
        </div>

        {/* Title */}
        <div
          style={{
            opacity: headerOpacity,
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            marginBottom: 12,
          }}
        >
          <span style={{ fontSize: 44 }}>📺</span>
          <div
            style={{
              fontFamily: FONTS.display,
              fontSize: 40,
              fontWeight: 700,
              color: COLORS.textPrimary,
            }}
          >
            YouTube Connection
          </div>
        </div>

        {/* Scope badges */}
        <div
          style={{
            opacity: headerOpacity,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 12,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 14,
              color: COLORS.textMuted,
              background: 'rgba(255,255,255,0.06)',
              padding: '6px 14px',
              borderRadius: 8,
            }}
          >
            youtube.upload + youtube
          </div>
          <div
            style={{
              padding: '4px 12px',
              borderRadius: 6,
              background: COLORS.scopeSensitiveBg,
              fontFamily: FONTS.mono,
              fontSize: 11,
              fontWeight: 700,
              color: '#92400e',
              letterSpacing: 1,
              textTransform: 'uppercase',
            }}
          >
            Sensitive
          </div>
        </div>

        {/* Key distinction callout */}
        <div
          style={{
            opacity: headerOpacity,
            fontFamily: FONTS.body,
            fontSize: 17,
            color: COLORS.textSecondary,
            marginBottom: 28,
            lineHeight: 1.5,
            padding: '12px 16px',
            background: 'rgba(234,179,8,0.08)',
            borderRadius: 12,
            border: '1px solid rgba(234,179,8,0.2)',
          }}
        >
          <strong style={{ color: '#fbbf24' }}>Separate OAuth Flow</strong> — YouTube uses
          a distinct connection via Settings &rarr; Social Accounts, not the main sign-in.
        </div>

        {/* Mock Social Accounts panel */}
        <div
          style={{
            flex: 1,
            background: 'rgba(0,0,0,0.25)',
            borderRadius: 16,
            padding: 24,
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 12,
              color: COLORS.textMuted,
              marginBottom: 16,
              letterSpacing: 1,
            }}
          >
            SETTINGS &rarr; SOCIAL ACCOUNTS
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <PlatformCard
              name="Twitter / X"
              icon="🐦"
              connected={false}
              delay={fps * 1.0}
            />
            <PlatformCard
              name="LinkedIn"
              icon="💼"
              connected={false}
              delay={fps * 1.3}
            />
            <PlatformCard
              name="YouTube"
              icon="▶️"
              connected={youtubeConnected}
              delay={fps * 1.6}
              highlight
            />
            <PlatformCard
              name="Instagram"
              icon="📸"
              connected={false}
              delay={fps * 1.9}
            />
            <PlatformCard
              name="TikTok"
              icon="🎵"
              connected={false}
              delay={fps * 2.2}
            />
          </div>
        </div>
      </div>

      {/* Right: Flow diagram + code */}
      <div
        style={{
          flex: 0.85,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 24,
        }}
      >
        {/* OAuth flow steps */}
        <div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 12,
              color: COLORS.textMuted,
              marginBottom: 14,
              letterSpacing: 1,
            }}
          >
            SEPARATE OAUTH 2.0 + PKCE FLOW
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <FlowStep
              step={1}
              label='User clicks "Connect YouTube"'
              sublabel="Settings page initiates OAuth"
              icon="👆"
              delay={fps * 3}
            />
            <FlowStep
              step={2}
              label="Google consent screen appears"
              sublabel="Shows youtube.upload + youtube scopes"
              icon="🔐"
              delay={fps * 3.8}
              highlight
            />
            <FlowStep
              step={3}
              label="User approves access"
              sublabel="PKCE code exchange via SocialConnector"
              icon="✅"
              delay={fps * 4.6}
            />
            <FlowStep
              step={4}
              label="Tokens stored securely"
              sublabel="connected_accounts table, encrypted at rest"
              icon="🗄️"
              delay={fps * 5.4}
            />
            <FlowStep
              step={5}
              label="Agent can publish videos"
              sublabel="Upload via YouTube Data API v3"
              icon="🚀"
              delay={fps * 6.2}
            />
          </div>
        </div>

        {/* Code snippet */}
        <div
          style={{
            opacity: interpolate(frame, [fps * 8, fps * 9], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            background: '#0d1117',
            borderRadius: 16,
            padding: 24,
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 11,
              color: COLORS.textMuted,
              marginBottom: 14,
              letterSpacing: 1,
            }}
          >
            SOCIAL CONNECTOR (BACKEND)
          </div>
          <pre
            style={{
              fontFamily: FONTS.mono,
              fontSize: 13,
              color: '#e2e8f0',
              lineHeight: 1.6,
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}
          >
            {`# Separate OAuth client for YouTube
PLATFORM_CONFIGS["youtube"] = {
    "scopes": [
        "youtube.upload",
        "youtube",
    ],
    "auth_url": "accounts.google.com/..."
}

# PKCE flow — distinct from main login
connector.get_authorization_url(
    platform="youtube",
    user_id=user_id,
    redirect_uri=callback_url
)`}
          </pre>
        </div>
      </div>
    </AbsoluteFill>
  );
};
