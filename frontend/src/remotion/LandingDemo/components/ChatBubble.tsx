import React from 'react';
import { useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';

interface ChatBubbleProps {
  sender: 'user' | 'agent';
  agentName?: string;
  agentEmoji?: string;
  text: string;
  appearFrame: number;
  isGreeting?: boolean;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  sender,
  agentName,
  agentEmoji,
  text,
  appearFrame,
  isGreeting,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const relFrame = frame - appearFrame;
  if (relFrame < 0) return null;

  const isUser = sender === 'user';
  const slideUp = spring({
    frame: relFrame,
    fps,
    config: { damping: 18, stiffness: 80 },
  });
  const opacity = interpolate(relFrame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const translateY = interpolate(slideUp, [0, 1], [30, 0]);

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 20,
        maxWidth: '85%',
        alignSelf: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      {/* Agent name label */}
      {!isUser && agentName && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 8,
            paddingLeft: 4,
          }}
        >
          <span style={{ fontSize: 22 }}>{agentEmoji}</span>
          <span
            style={{
              fontSize: 15,
              fontWeight: 700,
              color: COLORS.accent,
              fontFamily: FONTS.mono,
              letterSpacing: 0.5,
            }}
          >
            {agentName}
          </span>
        </div>
      )}

      {/* Message bubble */}
      <div
        style={{
          padding: isGreeting ? '20px 28px' : '16px 24px',
          borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
          background: isUser
            ? `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`
            : '#ffffff',
          border: isUser ? 'none' : `1px solid ${COLORS.border}`,
          borderLeft: isUser ? 'none' : `3px solid ${COLORS.accent}`,
          boxShadow: isUser
            ? '0 2px 12px rgba(26, 138, 110, 0.3)'
            : '0 2px 8px rgba(0, 0, 0, 0.06)',
        }}
      >
        <div
          style={{
            fontSize: isGreeting ? 26 : 22,
            lineHeight: 1.5,
            fontWeight: isGreeting ? 500 : 400,
            color: isUser ? '#ffffff' : COLORS.textDark,
            fontFamily: FONTS.body,
          }}
        >
          {text}
        </div>
      </div>

      {/* User label */}
      {isUser && (
        <div
          style={{
            marginTop: 6,
            paddingRight: 4,
            fontSize: 13,
            color: COLORS.textMuted,
            fontFamily: FONTS.mono,
          }}
        >
          You
        </div>
      )}
    </div>
  );
};
