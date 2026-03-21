import React from 'react';
import { AbsoluteFill } from 'remotion';
import { MockDashboardShell } from '../components/MockDashboardShell';
import { MockChatThread } from '../components/MockChatThread';
import { AgentOrchestration } from '../components/AgentOrchestration';
import { CaptionBar } from '../components/CaptionBar';
import { type PersonaSceneData } from '../data/personas';

interface PersonaSceneProps {
  data: PersonaSceneData;
}

export const PersonaScene: React.FC<PersonaSceneProps> = ({ data }) => {
  const isExecutive = data.id === 'enterprise';

  return (
    <AbsoluteFill>
      <MockDashboardShell
        personaTitle={data.title}
        personaEmoji={data.emoji}
        personaGradient={data.gradient}
        agents={data.agents}
        metrics={data.dashboardMetrics}
      >
        {isExecutive ? (
          <div style={{ display: 'flex', gap: 24, height: '100%' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <MockChatThread messages={data.chatMessages} />
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 320,
              }}
            >
              <AgentOrchestration size={300} />
            </div>
          </div>
        ) : (
          <MockChatThread messages={data.chatMessages} />
        )}
      </MockDashboardShell>
      <CaptionBar text={data.caption} appearFrame={30} />
    </AbsoluteFill>
  );
};
