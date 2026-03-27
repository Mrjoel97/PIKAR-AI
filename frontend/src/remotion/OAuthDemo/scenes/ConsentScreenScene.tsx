import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS, SCOPES } from '../constants';

const ScopeRow: React.FC<{
  scope: (typeof SCOPES)[number];
  delay: number;
}> = ({ scope, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [delay, delay + fps * 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const x = interpolate(frame, [delay, delay + fps * 0.3], [30, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const classColors = {
    basic: { bg: COLORS.scopeBasicBg, text: COLORS.scopeBasic, label: 'BASIC' },
    sensitive: { bg: COLORS.scopeSensitiveBg, text: COLORS.scopeSensitive, label: 'SENSITIVE' },
    restricted: { bg: COLORS.scopeRestrictedBg, text: COLORS.scopeRestricted, label: 'RESTRICTED' },
  };

  const cls = classColors[scope.classification];

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '14px 20px',
        background: 'rgba(255,255,255,0.03)',
        borderRadius: 12,
        marginBottom: 8,
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Icon */}
      <span style={{ fontSize: 24, width: 36, textAlign: 'center' }}>
        {'icon' in scope ? scope.icon : scope.classification === 'basic' ? '👤' : '🔑'}
      </span>

      {/* Scope info */}
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 18,
            fontWeight: 600,
            color: COLORS.textPrimary,
          }}
        >
          {scope.label}
        </div>
        <div
          style={{
            fontFamily: FONTS.mono,
            fontSize: 13,
            color: COLORS.textMuted,
            marginTop: 2,
          }}
        >
          {scope.scope.startsWith('gmail') || scope.scope === 'calendar'
            ? `googleapis.com/auth/${scope.scope}`
            : scope.scope}
        </div>
      </div>

      {/* Classification badge */}
      <div
        style={{
          padding: '4px 12px',
          borderRadius: 6,
          background: cls.bg,
          fontFamily: FONTS.mono,
          fontSize: 11,
          fontWeight: 700,
          color: cls.text,
          letterSpacing: 1,
        }}
      >
        {cls.label}
      </div>
    </div>
  );
};

export const ConsentScreenScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const consentCardScale = spring({
    frame: Math.max(0, frame - fps * 0.3),
    fps,
    config: { damping: 14, stiffness: 80 },
  });

  const sectionBadgeOpacity = interpolate(frame, [0, fps * 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Highlight pulse on restricted scopes after all appear
  const highlightFrame = fps * 7;
  const highlightOpacity = interpolate(
    frame,
    [highlightFrame, highlightFrame + fps * 0.5, highlightFrame + fps * 2, highlightFrame + fps * 2.5],
    [0, 0.15, 0.15, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${COLORS.bgDark} 0%, #0d3333 100%)`,
        padding: 80,
        display: 'flex',
        flexDirection: 'row',
        gap: 60,
      }}
    >
      {/* Left: title + description */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
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
          Section 2 of 7
        </div>

        <div
          style={{
            opacity: headerOpacity,
            fontFamily: FONTS.display,
            fontSize: 44,
            fontWeight: 700,
            color: COLORS.textPrimary,
            marginBottom: 24,
            lineHeight: 1.2,
          }}
        >
          Google OAuth{'\n'}Consent Screen
        </div>

        <div
          style={{
            opacity: headerOpacity,
            fontFamily: FONTS.body,
            fontSize: 20,
            color: COLORS.textSecondary,
            lineHeight: 1.6,
          }}
        >
          When a user clicks "Continue with Google", they see Google's consent screen listing
          all permissions Pikar AI is requesting. The user must explicitly grant each scope
          before the app receives access.
        </div>

        {/* Flow diagram */}
        <div
          style={{
            opacity: interpolate(frame, [fps * 6, fps * 7], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            marginTop: 40,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            fontFamily: FONTS.mono,
            fontSize: 14,
            color: COLORS.textMuted,
          }}
        >
          <span style={{ padding: '8px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.06)' }}>
            User clicks Allow
          </span>
          <span>&#8594;</span>
          <span style={{ padding: '8px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.06)' }}>
            Code sent to /auth/callback
          </span>
          <span>&#8594;</span>
          <span style={{ padding: '8px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.06)' }}>
            Supabase exchanges for tokens
          </span>
        </div>
      </div>

      {/* Right: mock consent card */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: `scale(${consentCardScale})`,
        }}
      >
        <div
          style={{
            width: 560,
            background: '#1e293b',
            borderRadius: 20,
            padding: 32,
            boxShadow: '0 30px 80px rgba(0,0,0,0.5)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          {/* Card header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginBottom: 24,
              paddingBottom: 20,
              borderBottom: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.teal600})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
              }}
            >
              &#9733;
            </div>
            <div>
              <div
                style={{
                  fontFamily: FONTS.display,
                  fontSize: 20,
                  fontWeight: 600,
                  color: COLORS.textPrimary,
                }}
              >
                Pikar AI wants to access your Google Account
              </div>
              <div
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 12,
                  color: COLORS.textMuted,
                  marginTop: 2,
                }}
              >
                pikar.ai
              </div>
            </div>
          </div>

          {/* Scope list */}
          <div style={{ position: 'relative' }}>
            {/* Highlight overlay for restricted scopes */}
            <div
              style={{
                position: 'absolute',
                inset: -8,
                borderRadius: 16,
                background: `rgba(239,68,68,${highlightOpacity})`,
                pointerEvents: 'none',
              }}
            />

            {SCOPES.map((scope, i) => (
              <ScopeRow key={scope.scope} scope={scope} delay={fps * 1.5 + i * fps * 0.5} />
            ))}
          </div>

          {/* Buttons */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 12,
              marginTop: 24,
              opacity: interpolate(frame, [fps * 5.5, fps * 6], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }),
            }}
          >
            <div
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.15)',
                fontFamily: FONTS.body,
                fontSize: 16,
                color: COLORS.textSecondary,
              }}
            >
              Cancel
            </div>
            <div
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                background: COLORS.googleBlue,
                fontFamily: FONTS.body,
                fontSize: 16,
                fontWeight: 600,
                color: '#fff',
              }}
            >
              Allow
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
