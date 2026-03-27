// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { COLORS, FONTS } from '../constants';
import { PersonaIntroCard } from '../components/PersonaIntroCard';
import { ChatBubble } from '../components/ChatBubble';
import { TypingIndicator } from '../components/TypingIndicator';
import { FloatingMetric } from '../components/FloatingMetric';
import { type PersonaSceneData } from '../data/personas';

interface PersonaSceneProps {
  data: PersonaSceneData;
}

export const PersonaScene: React.FC<PersonaSceneProps> = ({ data }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Chat area appears after intro card exits (frame 165)
  const chatOpacity = interpolate(frame, [165, 195], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Metrics appear near the end
  const metricsStart = fps * 26; // 26 seconds in

  // Build the chat sequence: typing dots -> greeting -> typing dots -> user message -> agent responses
  const greetingAgent = data.agents[0];
  const typingDotsDuration = Math.round(fps * 1.5); // 1.5s of dots

  // Timeline (frames from scene start):
  // 165: chat bg appears
  // 195: typing dots for greeting
  // 195 + typingDotsDuration: greeting message appears
  const greetingDotsFrame = 195;
  const greetingMsgFrame = greetingDotsFrame + typingDotsDuration;
  // User typing dots after greeting
  const userDotsFrame = greetingMsgFrame + Math.round(fps * 2);
  const userMsgFrame = userDotsFrame + typingDotsDuration;

  return (
    <AbsoluteFill>
      {/* Chat background (visible after intro card) */}
      <AbsoluteFill
        style={{
          backgroundColor: '#f8fafa',
          opacity: chatOpacity,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Subtle ambient glow */}
        <div
          style={{
            position: 'absolute',
            top: -200,
            right: -200,
            width: 600,
            height: 600,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${data.gradient[0]}10 0%, transparent 70%)`,
            filter: 'blur(100px)',
          }}
        />

        {/* Small persona label at top */}
        <div
          style={{
            padding: '20px 48px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            borderBottom: `1px solid ${COLORS.border}`,
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: `linear-gradient(135deg, ${COLORS.teal700}, ${COLORS.teal600})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ fontSize: 18 }}>{'\u{1F9E0}'}</span>
          </div>
          <span
            style={{
              fontSize: 18,
              fontWeight: 700,
              fontFamily: FONTS.display,
              color: COLORS.textDark,
            }}
          >
            Pikar <span style={{ color: COLORS.primary }}>AI</span>
          </span>
          <span
            style={{
              fontSize: 14,
              color: COLORS.textMuted,
              fontFamily: FONTS.mono,
              marginLeft: 8,
            }}
          >
            {data.title} Workspace
          </span>
          <div
            style={{
              marginLeft: 'auto',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: '#22c55e',
                boxShadow: '0 0 6px rgba(34,197,94,0.5)',
              }}
            />
            <span
              style={{
                fontSize: 12,
                color: COLORS.textMuted,
                fontFamily: FONTS.mono,
              }}
            >
              {data.agents.length} agents online
            </span>
          </div>
        </div>

        {/* Chat area -- centered, large text */}
        <div
          style={{
            flex: 1,
            padding: '32px 80px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            gap: 8,
            maxWidth: 1200,
            width: '100%',
            margin: '0 auto',
          }}
        >
          {/* Agent greeting: typing dots then message */}
          <TypingIndicator
            appearFrame={greetingDotsFrame}
            agentName={greetingAgent.name}
            agentEmoji={greetingAgent.emoji}
          />
          <ChatBubble
            sender="agent"
            agentName={greetingAgent.name}
            agentEmoji={greetingAgent.emoji}
            text={data.greeting}
            appearFrame={greetingMsgFrame}
            isGreeting
          />

          {/* User typing dots then message */}
          {frame >= userDotsFrame && frame < userMsgFrame && (
            <div
              style={{
                alignSelf: 'flex-end',
                display: 'flex',
                gap: 6,
                padding: '12px 20px',
                borderRadius: 16,
                backgroundColor: 'rgba(59, 191, 151, 0.15)',
              }}
            >
              {[0, 1, 2].map((i) => {
                const bounce = interpolate(
                  ((frame - userDotsFrame) + i * 5) % 30,
                  [0, 10, 20, 30],
                  [0, -8, 0, 0],
                  { extrapolateRight: 'clamp' },
                );
                return (
                  <div
                    key={i}
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      backgroundColor: COLORS.teal400,
                      transform: `translateY(${bounce}px)`,
                      opacity: 0.7,
                    }}
                  />
                );
              })}
            </div>
          )}
          <ChatBubble
            sender="user"
            text={data.chatMessages[0].text}
            appearFrame={userMsgFrame}
          />

          {/* Agent responses with typing dots before each */}
          {data.chatMessages.slice(1).map((msg, i) => {
            const msgDelay = userMsgFrame + Math.round((i + 1) * fps * 3.5);
            const dotsDelay = msgDelay - typingDotsDuration;
            return (
              <React.Fragment key={i}>
                <TypingIndicator
                  appearFrame={dotsDelay}
                  agentName={msg.agentName}
                  agentEmoji={
                    data.agents.find((a) => a.name === msg.agentName)?.emoji
                  }
                />
                <ChatBubble
                  sender="agent"
                  agentName={msg.agentName}
                  agentEmoji={
                    data.agents.find((a) => a.name === msg.agentName)?.emoji
                  }
                  text={msg.text}
                  appearFrame={msgDelay}
                />
              </React.Fragment>
            );
          })}
        </div>

        {/* Floating metrics at bottom */}
        {data.dashboardMetrics && (
          <div
            style={{
              position: 'absolute',
              bottom: 32,
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'center',
              gap: 20,
            }}
          >
            {data.dashboardMetrics.map((m, i) => (
              <FloatingMetric
                key={m.label}
                label={m.label}
                value={m.value}
                trend={m.trend}
                appearFrame={metricsStart + i * 10}
                index={i}
              />
            ))}
          </div>
        )}
      </AbsoluteFill>

      {/* Persona intro card (renders on top, exits at frame 165) */}
      <PersonaIntroCard
        title={data.title}
        subtitle={data.subtitle}
        emoji={data.emoji}
        gradient={data.gradient}
        tierFeatures={data.tierFeatures}
      />
    </AbsoluteFill>
  );
};
