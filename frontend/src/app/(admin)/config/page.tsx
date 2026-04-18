'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { AgentConfigEditor } from '@/components/admin/config/AgentConfigEditor';
import { VersionHistory } from '@/components/admin/config/VersionHistory';
import { FeatureFlagRow } from '@/components/admin/config/FeatureFlagRow';
import { AutonomyTable } from '@/components/admin/config/AutonomyTable';
import { McpEndpoints } from '@/components/admin/config/McpEndpoints';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Tab identifiers */
type Tab = 'instructions' | 'flags' | 'autonomy' | 'mcp';

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'instructions', label: 'Instructions' },
  { id: 'flags', label: 'Feature Flags' },
  { id: 'autonomy', label: 'Autonomy' },
  { id: 'mcp', label: 'MCP Endpoints' },
];

/** Shape of an agent summary from GET /admin/config/agents */
interface AgentSummary {
  agent_name: string;
  version: number;
  updated_at: string;
}

/** Shape of a feature flag from GET /admin/config/flags */
interface FeatureFlag {
  flag_key: string;
  is_enabled: boolean;
  description: string | null;
  updated_at: string;
}

/**
 * ConfigPage renders /admin/config with a 4-tab interface:
 * - Instructions: per-agent instruction editor with diff preview + version history
 * - Feature Flags: toggle switches for all feature flags
 * - Autonomy: tier assignment table for all admin actions
 * - MCP Endpoints: read-only MCP endpoint list
 */
export default function ConfigPage() {
  const supabase = createClient();

  const [activeTab, setActiveTab] = useState<Tab>('instructions');
  const [token, setToken] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  // Instructions tab state
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [editorKey, setEditorKey] = useState(0); // bump to force editor remount

  // Feature flags state
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [isLoadingFlags, setIsLoadingFlags] = useState(false);
  const [flagsError, setFlagsError] = useState<string | null>(null);

  // ─── Get auth token ────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    const loadSession = async () => {
      const { data } = await supabase.auth.getSession();
      if (cancelled) {
        return;
      }

      const session = data.session;
      if (!session) {
        setAuthError('Not authenticated. Please sign in to access config.');
        return;
      }

      setToken(session.access_token);
    };

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, [supabase]);

  // ─── Fetch agents list ─────────────────────────────────────────────────────

  const fetchAgents = useCallback(async (currentToken: string) => {
    setIsLoadingAgents(true);
    setAgentsError(null);
    try {
      const res = await fetch(`${API_URL}/admin/config/agents`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      });
      if (!res.ok) {
        setAgentsError(`Failed to load agents (${res.status})`);
        return;
      }
      const data = (await res.json()) as AgentSummary[];
      setAgents(data);
      if (data.length > 0 && !selectedAgent) {
        setSelectedAgent(data[0].agent_name);
      }
    } catch {
      setAgentsError('Failed to load agents. Check that the backend is running.');
    } finally {
      setIsLoadingAgents(false);
    }
  }, [selectedAgent]);

  useEffect(() => {
    if (token) {
      fetchAgents(token);
    }
  }, [token, fetchAgents]);

  // ─── Fetch feature flags ───────────────────────────────────────────────────

  const fetchFlags = useCallback(async (currentToken: string) => {
    setIsLoadingFlags(true);
    setFlagsError(null);
    try {
      const res = await fetch(`${API_URL}/admin/config/flags`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      });
      if (!res.ok) {
        setFlagsError(`Failed to load feature flags (${res.status})`);
        return;
      }
      const data = (await res.json()) as FeatureFlag[];
      setFlags(data);
    } catch {
      setFlagsError('Failed to load feature flags. Check that the backend is running.');
    } finally {
      setIsLoadingFlags(false);
    }
  }, []);

  // Load flags when switching to that tab
  useEffect(() => {
    if (activeTab === 'flags' && token && flags.length === 0 && !isLoadingFlags) {
      fetchFlags(token);
    }
  }, [activeTab, token, flags.length, isLoadingFlags, fetchFlags]);

  // ─── Feature flag toggle handler ─────────────────────────────────────────

  const handleFlagToggle = useCallback((key: string, enabled: boolean) => {
    setFlags((prev) =>
      prev.map((f) => (f.flag_key === key ? { ...f, is_enabled: enabled } : f)),
    );
  }, []);

  // ─── Agent editor refresh (after rollback) ────────────────────────────────

  const handleRollback = useCallback(() => {
    setEditorKey((k) => k + 1);
  }, []);

  // ─── Render ───────────────────────────────────────────────────────────────

  if (authError) {
    return (
      <div className="p-8">
        <p className="text-red-400 text-sm">{authError}</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Agent Configuration</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Manage agent instructions, feature flags, autonomy tiers, and MCP endpoints
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-gray-700 mb-6 bg-gray-800/50 rounded-t-lg">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-3 text-sm font-medium transition-colors relative focus:outline-none ${
              activeTab === tab.id
                ? 'text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
            aria-selected={activeTab === tab.id}
            role="tab"
          >
            {tab.label}
            {/* Active indicator */}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-sm" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div role="tabpanel">
        {/* ── Instructions tab ── */}
        {activeTab === 'instructions' && (
          <div className="space-y-6">
            {/* Agent selector */}
            <div className="flex items-center gap-4">
              <label
                htmlFor="agent-select"
                className="text-sm font-medium text-gray-300 shrink-0"
              >
                Agent
              </label>
              {isLoadingAgents ? (
                <div className="bg-gray-800 rounded-lg h-9 w-48 animate-pulse" />
              ) : agentsError ? (
                <p className="text-red-400 text-sm">{agentsError}</p>
              ) : (
                <select
                  id="agent-select"
                  value={selectedAgent}
                  onChange={(e) => {
                    setSelectedAgent(e.target.value);
                    setEditorKey((k) => k + 1);
                  }}
                  className="bg-gray-800 border border-gray-600 text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent min-w-[200px]"
                >
                  {agents.map((agent) => (
                    <option key={agent.agent_name} value={agent.agent_name}>
                      {agent.agent_name.charAt(0).toUpperCase() +
                        agent.agent_name.slice(1)}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Editor + version history */}
            {selectedAgent && token && (
              <>
                <AgentConfigEditor
                  key={`editor-${selectedAgent}-${editorKey}`}
                  agentName={selectedAgent}
                  token={token}
                  onSaved={handleRollback}
                />
                <VersionHistory
                  key={`history-${selectedAgent}-${editorKey}`}
                  agentName={selectedAgent}
                  token={token}
                  onRollback={handleRollback}
                />
              </>
            )}
          </div>
        )}

        {/* ── Feature Flags tab ── */}
        {activeTab === 'flags' && (
          <div>
            {isLoadingFlags && (
              <div className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="bg-gray-800 rounded-lg h-16 animate-pulse" />
                ))}
              </div>
            )}

            {flagsError && !isLoadingFlags && (
              <div className="flex flex-col items-center justify-center py-12 gap-4">
                <p className="text-red-400 text-sm">{flagsError}</p>
                {token && (
                  <button
                    type="button"
                    onClick={() => fetchFlags(token)}
                    className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
                  >
                    Retry
                  </button>
                )}
              </div>
            )}

            {!isLoadingFlags && !flagsError && flags.length === 0 && (
              <p className="text-center text-gray-500 text-sm py-12">
                No feature flags configured.
              </p>
            )}

            {!isLoadingFlags && flags.length > 0 && token && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg px-4 divide-y divide-gray-700">
                {flags.map((flag) => (
                  <FeatureFlagRow
                    key={flag.flag_key}
                    flagKey={flag.flag_key}
                    isEnabled={flag.is_enabled}
                    description={flag.description}
                    token={token}
                    onToggle={handleFlagToggle}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Autonomy tab ── */}
        {activeTab === 'autonomy' && token && (
          <AutonomyTable token={token} />
        )}

        {/* ── MCP Endpoints tab ── */}
        {activeTab === 'mcp' && token && (
          <McpEndpoints token={token} />
        )}
      </div>
    </div>
  );
}
