'use client';

import { useState, useEffect, useCallback } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import DashboardSkeleton from '@/components/ui/DashboardSkeleton';
import { motion } from 'framer-motion';
import {
    Cpu,
    Key,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Trash2,
    ExternalLink,
    ChevronRight,
    Sparkles,
    Shield,
} from 'lucide-react';
import Link from 'next/link';
import { fetchWithAuth } from '@/services/api';

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

function ProviderCard({
    id,
    info,
    isSelected,
    onSelect,
}: {
    id: string;
    info: ProviderInfo;
    isSelected: boolean;
    onSelect: (id: string) => void;
}) {
    const icons: Record<string, string> = {
        openai: '🟢',
        anthropic: '🟠',
    };

    return (
        <button
            onClick={() => onSelect(id)}
            className={`p-4 rounded-2xl border-2 transition-all text-left w-full ${
                isSelected
                    ? 'border-teal-500 bg-teal-50 shadow-lg shadow-teal-500/10'
                    : 'border-slate-100 bg-white hover:border-slate-200 shadow-[0_4px_24px_-12px_rgba(15,23,42,0.08)]'
            }`}
        >
            <div className="flex items-center gap-3">
                <span className="text-2xl">{icons[id] || '🔑'}</span>
                <div>
                    <h3 className="font-semibold text-slate-900">{info.name}</h3>
                    <p className="text-xs text-slate-500">Key prefix: {info.key_prefix}...</p>
                </div>
                {isSelected && <CheckCircle2 className="h-5 w-5 text-teal-500 ml-auto" />}
            </div>
        </button>
    );
}

export default function AIProviderPage() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
    const [status, setStatus] = useState<BYOKStatus>({ enabled: false, provider: null, model: null, org_id: null });
    const [models, setModels] = useState<ModelOption[]>([]);

    const [selectedProvider, setSelectedProvider] = useState<string>('');
    const [selectedModel, setSelectedModel] = useState<string>('');
    const [apiKey, setApiKey] = useState<string>('');
    const [orgId, setOrgId] = useState<string>('');

    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [saveSuccess, setSaveSuccess] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const [providersRes, statusRes] = await Promise.all([
                fetchWithAuth('/byok/providers'),
                fetchWithAuth('/byok/status'),
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
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        if (!selectedProvider) {
            setModels([]);
            return;
        }
        (async () => {
            try {
                const res = await fetchWithAuth(`/byok/models/${selectedProvider}`);
                const data = await res.json();
                setModels(data);
                if (data.length > 0 && !selectedModel) {
                    setSelectedModel(data[0].id);
                }
            } catch {
                setModels([]);
            }
        })();
    }, [selectedProvider]);

    const handleTest = async () => {
        if (!apiKey || !selectedProvider || !selectedModel) return;
        setTesting(true);
        setTestResult(null);
        try {
            const res = await fetchWithAuth('/byok/test', {
                method: 'POST',
                body: JSON.stringify({
                    provider: selectedProvider,
                    model: selectedModel,
                    api_key: apiKey,
                    org_id: orgId || null,
                }),
            });
            const data = await res.json();
            setTestResult(data);
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
            const res = await fetchWithAuth('/byok/save', {
                method: 'POST',
                body: JSON.stringify({
                    provider: selectedProvider,
                    model: selectedModel,
                    api_key: apiKey,
                    org_id: orgId || null,
                }),
            });
            const data = await res.json();
            if (data.success) {
                setSaveSuccess(true);
                setApiKey('');
                setStatus({ enabled: true, provider: selectedProvider, model: selectedModel, org_id: orgId || null });
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
        setDeleting(true);
        try {
            await fetchWithAuth('/byok/delete', { method: 'DELETE' });
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
            <PremiumShell>
                <DashboardSkeleton rows={3} columns={1} showMetricCards={false} />
            </PremiumShell>
        );
    }

    return (
        <DashboardErrorBoundary fallbackTitle="AI Provider Settings Error">
            <PremiumShell>
                <div className="max-w-3xl mx-auto space-y-6">
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                    >
                        <div className="flex items-center gap-2 mb-3 text-sm">
                            <Link href="/settings" className="text-slate-500 hover:text-slate-700">Settings</Link>
                            <ChevronRight className="h-4 w-4 text-slate-400" />
                            <span className="text-slate-900">AI Provider</span>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg">
                                <Cpu className="h-6 w-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-semibold tracking-tight text-slate-900">AI Provider</h1>
                                <p className="mt-0.5 text-sm text-slate-500">
                                    Bring your own API key to use OpenAI, Anthropic, or other providers
                                </p>
                            </div>
                        </div>
                    </motion.div>

                    {status.enabled && (
                        <motion.div
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="rounded-2xl border border-teal-200 bg-teal-50 p-5"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-teal-600" />
                                    <div>
                                        <p className="text-sm font-semibold text-teal-900">
                                            BYOK Active: {providers[status.provider!]?.name || status.provider}
                                        </p>
                                        <p className="text-xs text-teal-700">Model: {status.model}</p>
                                    </div>
                                </div>
                                <button
                                    onClick={handleDelete}
                                    disabled={deleting}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-rose-700 bg-white border border-rose-200 rounded-lg hover:bg-rose-50 transition-colors disabled:opacity-50"
                                >
                                    <Trash2 className="h-3 w-3" />
                                    {deleting ? 'Removing...' : 'Remove'}
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {error && (
                        <div className="flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-3">
                            <AlertCircle className="h-5 w-5 text-rose-500" />
                            <p className="text-sm text-rose-700">{error}</p>
                        </div>
                    )}

                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.05 }}
                        className="rounded-2xl border border-blue-100 bg-blue-50/50 p-4 flex items-start gap-3"
                    >
                        <Shield className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
                        <p className="text-sm text-blue-800">
                            Your API key is encrypted at rest with AES-256 and never exposed to the frontend.
                            It is used server-side only to route your requests to your chosen provider.
                        </p>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                    >
                        <div className="flex items-center gap-3 mb-5">
                            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-400 to-purple-500 shadow-lg">
                                <Sparkles className="h-5 w-5 text-white" />
                            </div>
                            <h2 className="text-lg font-semibold text-slate-900">Choose Provider</h2>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
                            {Object.entries(providers).map(([id, info]) => (
                                <ProviderCard
                                    key={id}
                                    id={id}
                                    info={info}
                                    isSelected={selectedProvider === id}
                                    onSelect={(pid) => {
                                        setSelectedProvider(pid);
                                        setSelectedModel('');
                                        setTestResult(null);
                                    }}
                                />
                            ))}
                        </div>

                        {selectedProvider && models.length > 0 && (
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-slate-700 mb-1.5">Model</label>
                                <select
                                    value={selectedModel}
                                    onChange={(e) => setSelectedModel(e.target.value)}
                                    className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none"
                                >
                                    {models.map((m) => (
                                        <option key={m.id} value={m.id}>
                                            {m.name} ({m.tier})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {selectedProvider && (
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                                        <Key className="h-4 w-4 inline mr-1" />
                                        API Key
                                    </label>
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder={`${providers[selectedProvider]?.key_prefix || ''}...`}
                                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 min-h-[44px] text-sm text-slate-900 font-mono focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none"
                                    />
                                    {providers[selectedProvider]?.docs_url && (
                                        <a
                                            href={providers[selectedProvider].docs_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center gap-1 text-xs text-teal-600 hover:underline mt-1.5"
                                        >
                                            Where do I find my API key? <ExternalLink className="h-3 w-3" />
                                        </a>
                                    )}
                                </div>

                                {selectedProvider === 'openai' && (
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-1.5">
                                            Organization ID (optional)
                                        </label>
                                        <input
                                            type="text"
                                            value={orgId}
                                            onChange={(e) => setOrgId(e.target.value)}
                                            placeholder="org-..."
                                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 min-h-[44px] text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none"
                                        />
                                    </div>
                                )}

                                {testResult && (
                                    <div className={`p-4 rounded-xl ${testResult.success ? 'bg-emerald-50 border border-emerald-200' : 'bg-rose-50 border border-rose-200'}`}>
                                        <div className="flex items-center gap-2">
                                            {testResult.success ? (
                                                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                            ) : (
                                                <AlertCircle className="h-5 w-5 text-rose-600" />
                                            )}
                                            <p className={`text-sm font-medium ${testResult.success ? 'text-emerald-800' : 'text-rose-800'}`}>
                                                {testResult.message}
                                            </p>
                                        </div>
                                    </div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    <button
                                        onClick={handleTest}
                                        disabled={!apiKey || testing}
                                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 min-h-[44px] text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-all disabled:opacity-50"
                                    >
                                        {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                                        {testing ? 'Testing...' : 'Test Connection'}
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        disabled={!apiKey || !selectedModel || saving}
                                        className={`inline-flex items-center gap-2 rounded-xl px-6 py-2.5 min-h-[44px] text-sm font-semibold text-white shadow-lg transition-all disabled:opacity-50 ${
                                            saveSuccess
                                                ? 'bg-emerald-600 shadow-emerald-600/25'
                                                : 'bg-teal-600 shadow-teal-600/25 hover:bg-teal-700'
                                        }`}
                                    >
                                        {saveSuccess ? (
                                            <><CheckCircle2 className="h-4 w-4" /> Saved!</>
                                        ) : saving ? (
                                            <><Loader2 className="h-4 w-4 animate-spin" /> Saving...</>
                                        ) : (
                                            'Save & Activate'
                                        )}
                                    </button>
                                </div>
                            </div>
                        )}
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="rounded-2xl bg-gradient-to-r from-violet-50 to-purple-50 border border-violet-100 p-5"
                    >
                        <h3 className="font-semibold text-slate-900 mb-2">How it works</h3>
                        <ul className="text-sm text-slate-600 space-y-1.5">
                            <li>1. Choose a provider and enter your API key</li>
                            <li>2. Test the connection to verify your key works</li>
                            <li>3. Save to activate — all future AI responses will use your provider</li>
                            <li>4. You can switch back to the default (Gemini) at any time by removing your key</li>
                        </ul>
                    </motion.div>
                </div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
