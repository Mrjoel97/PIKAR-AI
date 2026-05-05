// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  ExternalLink,
  Eye,
  EyeOff,
  Key,
  Loader2,
  Shield,
  Trash2,
} from 'lucide-react';
import { createClient } from '@/lib/supabase/client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProviderInfo {
  name: string;
  key_prefix: string;
  env_var: string;
  docs_url: string;
}

interface ModelOption {
  id: string;
  name: string;
  tier: string;
}

interface BYOKStatus {
  enabled: boolean;
  provider: string | null;
  model: string | null;
  org_id: string | null;
}

const PROVIDER_BADGE: Record<string, string> = {
  openai: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  anthropic: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
};

export default function AIProviderPage() {
  const supabase = createClient();
  const [token, setToken] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [status, setStatus] = useState<BYOKStatus>({
    enabled: false,
    provider: null,
    model: null,
    org_id: null,
  });
  const [models, setModels] = useState<ModelOption[]>([]);

  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [apiKey, setApiKey] = useState<string>('');
  const [showKey, setShowKey] = useState(false);
  const [orgId, setOrgId] = useState<string>('');

  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const authedFetch = useCallback(
    async (path: string, init?: RequestInit) => {
      if (!token) throw new Error('No session');
      return fetch(`${API_URL}${path}`, {
        ...init,
        headers: {
          ...init?.headers,
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
    },
    [token],
  );

  // Load session
  useEffect(() => {
    (async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) setToken(session.access_token);
      else setError('Not authenticated');
    })();
  }, [supabase]);

  // Load providers + status
  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [providersRes, statusRes] = await Promise.all([
        authedFetch('/byok/providers'),
        authedFetch('/byok/status'),
      ]);
      const providersData = await providersRes.json();
      const statusData = await statusRes.json();
      setProviders(providersData);
      setStatus(statusData);
      if (statusData.enabled && statusData.provider) {
        setSelectedProvider(statusData.provider);
        setSelectedModel(statusData.model || '');
        setOrgId(statusData.org_id || '');
      }
    } catch {
      setError('Failed to load BYOK settings');
    } finally {
      setLoading(false);
    }
  }, [token, authedFetch]);

  useEffect(() => {
    if (token) fetchData();
  }, [token, fetchData]);

  // Load models when provider changes
  useEffect(() => {
    if (!token || !selectedProvider) {
      setModels([]);
      return;
    }
    (async () => {
      try {
        const res = await authedFetch(`/byok/models/${selectedProvider}`);
        const data = await res.json();
        setModels(data);
        if (data.length > 0 && !selectedModel) {
          setSelectedModel(data[0].id);
        }
      } catch {
        setModels([]);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedProvider]);

  const handleTest = async () => {
    if (!apiKey || !selectedProvider || !selectedModel) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await authedFetch('/byok/test', {
        method: 'POST',
        body: JSON.stringify({
          provider: selectedProvider,
          model: selectedModel,
          api_key: apiKey,
          org_id: orgId || null,
        }),
      });
      setTestResult(await res.json());
    } catch {
      setTestResult({ success: false, message: 'Network error' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey || !selectedProvider || !selectedModel) return;
    setSaving(true);
    setError(null);
    try {
      const res = await authedFetch('/byok/save', {
        method: 'POST',
        body: JSON.stringify({
          provider: selectedProvider,
          model: selectedModel,
          api_key: apiKey,
          org_id: orgId || null,
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setSaveSuccess(true);
        setApiKey('');
        setStatus({
          enabled: true,
          provider: selectedProvider,
          model: selectedModel,
          org_id: orgId || null,
        });
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        setError(data.detail || 'Save failed');
      }
    } catch {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Remove your BYOK key? Your agents will revert to platform Gemini.')) return;
    setDeleting(true);
    try {
      await authedFetch('/byok/delete', { method: 'DELETE' });
      setStatus({ enabled: false, provider: null, model: null, org_id: null });
      setSelectedProvider('');
      setSelectedModel('');
      setApiKey('');
      setOrgId('');
      setTestResult(null);
    } catch {
      setError('Failed to delete');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-3xl">
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-800/50 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600">
          <Cpu className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">AI Provider</h1>
          <p className="mt-1 text-sm text-gray-400">
            Bring your own API key. Without one, the admin agent uses platform Gemini.
          </p>
        </div>
      </div>

      {/* Active config */}
      {status.enabled && (
        <div className="rounded-xl border border-teal-500/30 bg-teal-500/5 p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-teal-400" />
              <div>
                <p className="text-sm font-semibold text-teal-200">
                  BYOK active: {providers[status.provider!]?.name || status.provider}
                </p>
                <p className="text-xs text-teal-300/70">Model: {status.model}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-rose-200 bg-rose-500/10 border border-rose-500/30 rounded-lg hover:bg-rose-500/20 disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deleting ? 'Removing…' : 'Remove'}
            </button>
          </div>
        </div>
      )}

      {/* Status banner */}
      {!status.enabled && (
        <div className="rounded-xl border border-gray-700 bg-gray-900 p-4 flex items-start gap-3">
          <Shield className="h-5 w-5 text-blue-400 mt-0.5 shrink-0" />
          <p className="text-sm text-gray-300">
            No BYOK configured. Admin agent currently uses platform <span className="text-gray-100 font-medium">Gemini 2.5 Pro</span> (with Flash failover). Add a key below to use OpenAI or Anthropic instead.
          </p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/5 px-4 py-3">
          <AlertCircle className="h-5 w-5 text-rose-400" />
          <p className="text-sm text-rose-300">{error}</p>
        </div>
      )}

      {saveSuccess && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-4 py-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          <p className="text-sm text-emerald-300">Saved. Your next agent message will use this provider.</p>
        </div>
      )}

      {/* Provider selection */}
      <div className="rounded-xl border border-gray-700 bg-gray-900 p-6 space-y-5">
        <div>
          <h2 className="text-sm font-semibold text-gray-200 mb-3">Choose provider</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(providers).map(([id, info]) => {
              const isSelected = selectedProvider === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setSelectedProvider(id);
                    setSelectedModel('');
                    setTestResult(null);
                  }}
                  className={`text-left rounded-xl border p-4 transition-all ${
                    isSelected
                      ? 'border-teal-500 bg-teal-500/5'
                      : 'border-gray-700 bg-gray-950 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-100">{info.name}</p>
                      <p className="mt-1 text-xs text-gray-500 font-mono">{info.key_prefix}…</p>
                    </div>
                    <span
                      className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                        PROVIDER_BADGE[id] || 'bg-gray-700 text-gray-300 border-gray-600'
                      }`}
                    >
                      {id}
                    </span>
                  </div>
                  <a
                    href={info.docs_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="mt-3 inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300"
                  >
                    Get an API key <ExternalLink className="h-3 w-3" />
                  </a>
                </button>
              );
            })}
          </div>
        </div>

        {/* Model + key */}
        {selectedProvider && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Model</label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              >
                {models.length === 0 && <option value="">Loading…</option>}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.tier})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                API key
                <span className="ml-2 text-[10px] font-normal text-gray-600">
                  encrypted server-side, never exposed to the browser after save
                </span>
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    providers[selectedProvider]?.key_prefix
                      ? `${providers[selectedProvider].key_prefix}…`
                      : 'Paste your key'
                  }
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 pl-10 pr-10 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 font-mono"
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowKey((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {selectedProvider === 'openai' && (
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">
                  Organization ID <span className="text-gray-600">(optional)</span>
                </label>
                <input
                  type="text"
                  value={orgId}
                  onChange={(e) => setOrgId(e.target.value)}
                  placeholder="org-…"
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 font-mono"
                />
              </div>
            )}

            {testResult && (
              <div
                className={`flex items-start gap-3 rounded-lg border px-4 py-3 ${
                  testResult.success
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : 'border-rose-500/30 bg-rose-500/5'
                }`}
              >
                {testResult.success ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                )}
                <p className={`text-sm ${testResult.success ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {testResult.message}
                </p>
              </div>
            )}

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={handleTest}
                disabled={testing || !apiKey || !selectedModel}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-100 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testing && <Loader2 className="h-4 w-4 animate-spin" />}
                {testing ? 'Testing…' : 'Test connection'}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !apiKey || !selectedModel}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-500 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {saving ? 'Saving…' : 'Save key'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
