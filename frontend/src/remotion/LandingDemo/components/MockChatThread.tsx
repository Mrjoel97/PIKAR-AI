import React from 'react';
import { useVideoConfig } from 'remotion';
import { ChatBubble } from './ChatBubble';
import { type ChatMessage } from '../data/personas';

interface MockChatThreadProps {
  messages: ChatMessage[];
}

export const MockChatThread: React.FC<MockChatThreadProps> = ({ messages }) => {
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {messages.map((msg, i) => (
        <ChatBubble key={i} sender={msg.sender} agentName={msg.agentName} text={msg.text} appearFrame={Math.round(msg.delaySeconds * fps)} />
      ))}
    </div>
  );
};
