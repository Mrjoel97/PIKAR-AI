'use client';

/** Generate a deterministic hue from an agent name string. */
function agentHue(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % 360;
}

interface AgentKnowledgeCardsProps {
  /**
   * Map of agent_scope → entry count.
   * The key "global" represents entries with no specific agent scope.
   */
  byAgent: Record<string, number>;
}

/**
 * AgentKnowledgeCards renders a responsive grid of cards showing
 * how many knowledge entries each agent has been trained on.
 */
export function AgentKnowledgeCards({ byAgent }: AgentKnowledgeCardsProps) {
  const entries = Object.entries(byAgent);

  if (entries.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 text-center">
        <p className="text-gray-500 text-sm">No per-agent knowledge yet.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {entries.map(([agent, count]) => {
        const displayName =
          agent === 'global'
            ? 'Global'
            : agent
                .replace(/_/g, ' ')
                .replace(/\b\w/g, (c) => c.toUpperCase());
        const hue = agentHue(agent);
        const dotColor = `hsl(${hue}, 60%, 55%)`;

        return (
          <div
            key={agent}
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 flex items-center gap-3"
          >
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: dotColor }}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-200 truncate">
                {displayName}
              </p>
              <p className="text-xs text-gray-400">
                {count.toLocaleString()} {count === 1 ? 'entry' : 'entries'}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
