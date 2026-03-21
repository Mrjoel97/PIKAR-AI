import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { TypewriterText } from './TypewriterText';
import { COLORS, FONTS } from '../constants';

interface ChatBubbleProps {
  sender: 'user' | 'agent';
  agentName?: string;
  text: string;
  appearFrame: number;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ sender, agentName, text, appearFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - appearFrame;
  if (localFrame < 0) return null;

  const slideIn = spring({ frame: localFrame, fps, config: { damping: 20, stiffness: 120, mass: 0.5 } });
  const translateY = interpolate(slideIn, [0, 1], [30, 0]);
  const opacity = interpolate(localFrame, [0, 8], [0, 1], { extrapolateRight: 'clamp' });
  const isUser = sender === 'user';

  return (
    <div style={{
      display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start',
      opacity, transform: `translateY(${translateY}px)`,
      marginBottom: 12, paddingLeft: isUser ? 80 : 0, paddingRight: isUser ? 0 : 80,
    }}>
      <div style={{
        maxWidth: 520, padding: '14px 18px',
        borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isUser
          ? `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`
          : COLORS.bgCard,
        borderLeft: isUser ? 'none' : `3px solid ${COLORS.accent}`,
        border: isUser ? 'none' : undefined,
        boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
      }}>
        {!isUser && agentName && (
          <div style={{
            fontSize: 13, fontWeight: 700, color: COLORS.accent,
            marginBottom: 6, fontFamily: FONTS.mono,
          }}>
            {agentName}
          </div>
        )}
        <TypewriterText text={text} startFrame={0} charsPerFrame={0.8} showCursor={!isUser}
          style={{
            fontSize: 16, lineHeight: '1.5',
            color: isUser ? COLORS.textPrimary : COLORS.textSecondary,
            fontFamily: FONTS.body, fontWeight: 400,
          }}
        />
      </div>
    </div>
  );
};
