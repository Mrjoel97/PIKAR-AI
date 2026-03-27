'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import PremiumShell from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  Key,
  Plus,
  Trash2,
  ArrowLeft,
  Shield,
  Eye,
  EyeOff,
} from 'lucide-react';
import { fetchWithAuth } from '@/services/api';

interface ApiCredential {
  id: string;
  name: string;
  auth_scheme: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

const AUTH_SCHEME_LABELS: Record<string, string> = {
  api_key: 'API Key',
  bearer: 'Bearer Token',
  basic: 'Basic Auth',
  oauth2: 'OAuth 2.0',
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/* ---------- Add Credential Form ---------- */

function AddCredentialForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (name: string, value: string, authScheme: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [authScheme, setAuthScheme] = useState('api_key');
  const [showValue, setShowValue] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !value.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(name.trim(), value, authScheme);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] space-y-4">
      <h3 className="text-sm font-semibold text-slate-900">Add API Credential</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. STRIPE_API_KEY"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-400"
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Auth Scheme</label>
          <select
            value={authScheme}
            onChange={(e) => setAuthScheme(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-400"
          >
            {Object.entries(AUTH_SCHEME_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Value</label>
        <div className="relative">
          <input
            type={showValue ? 'text' : 'password'}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="sk-..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 pr-10 text-sm text-slate-900 outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-400"
            required
          />
          <button
            type="button"
            onClick={() => setShowValue(!showValue)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            {showValue ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submitting || !name.trim() || !value.trim()}
          className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-50"
        >
          <Shield className="h-4 w-4" />
          {submitting ? 'Saving...' : 'Save Credential'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-2xl px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/* ---------- Main page ---------- */

export default function ApiConnectionsPage() {
  const [credentials, setCredentials] = useState<ApiCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadCredentials = useCallback(async () => {
    try {
      const response = await fetchWithAuth('/api-credentials');
      const data = await response.json();
      setCredentials(data);
    } catch (err) {
      console.error('Failed to load credentials:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCredentials();
  }, [loadCredentials]);

  const handleCreate = async (name: string, value: string, authScheme: string) => {
    await fetchWithAuth('/api-credentials', {
      method: 'POST',
      body: JSON.stringify({ name, value, auth_scheme: authScheme }),
    });
    setShowForm(false);
    await loadCredentials();
  };

  const handleDelete = async (name: string) => {
    setDeleting(name);
    try {
      await fetchWithAuth(`/api-credentials/${encodeURIComponent(name)}`, {
        method: 'DELETE',
      });
      await loadCredentials();
    } catch (err) {
      console.error('Failed to delete credential:', err);
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="API Connections Error">
        <PremiumShell>
          <div className="mx-auto max-w-7xl space-y-8">
            <div className="h-8 w-56 animate-pulse rounded-xl bg-slate-200" />
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-[28px] bg-slate-100" />
              ))}
            </div>
          </div>
        </PremiumShell>
      </DashboardErrorBoundary>
    );
  }

  return (
    <DashboardErrorBoundary fallbackTitle="API Connections Error">
      <PremiumShell>
        <motion.div
          className="mx-auto max-w-7xl space-y-8"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                href="/settings/integrations"
                className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              >
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                API Credentials
              </h1>
            </div>
            {!showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-teal-700"
              >
                <Plus className="h-4 w-4" />
                Add Credential
              </button>
            )}
          </div>

          {/* Add Form */}
          {showForm && (
            <AddCredentialForm
              onSubmit={handleCreate}
              onCancel={() => setShowForm(false)}
            />
          )}

          {/* Credential List */}
          <section className="space-y-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              Stored Credentials ({credentials.length})
            </h2>
            {credentials.length === 0 ? (
              <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                <Key className="mx-auto h-10 w-10 text-slate-300" />
                <p className="mt-3 text-sm font-medium text-slate-600">No credentials stored</p>
                <p className="mt-1 text-xs text-slate-400">Add API keys so agents can access external services</p>
              </div>
            ) : (
              <div className="space-y-3">
                {credentials.map((cred) => (
                  <div
                    key={cred.id}
                    className="flex items-center justify-between rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex-shrink-0 rounded-2xl bg-gradient-to-br from-teal-400 to-emerald-500 p-3 shadow-lg">
                        <Key className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">{cred.name}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <StatusBadge status={cred.auth_scheme === 'api_key' ? 'active' : cred.auth_scheme} />
                          <span className="text-xs text-slate-400">
                            {AUTH_SCHEME_LABELS[cred.auth_scheme] || cred.auth_scheme}
                          </span>
                          <span className="text-xs text-slate-400">
                            Added {formatDate(cred.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(cred.name)}
                      disabled={deleting === cred.name}
                      className="rounded-xl p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                      title="Delete credential"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </motion.div>
      </PremiumShell>
    </DashboardErrorBoundary>
  );
}
