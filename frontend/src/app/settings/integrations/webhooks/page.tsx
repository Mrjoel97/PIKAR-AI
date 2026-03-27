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
  Webhook,
  ArrowLeft,
  Clock,
  Filter,
} from 'lucide-react';
import { fetchWithAuth } from '@/services/api';

interface WebhookEvent {
  id: string;
  platform: string;
  event_type: string;
  status: string;
  received_at: string;
  processed_at: string | null;
}

const PLATFORMS = ['all', 'linkedin', 'twitter', 'facebook', 'instagram', 'tiktok', 'youtube'];
const STATUSES = ['all', 'pending', 'processing', 'processed', 'failed', 'ignored'];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function WebhookEventsPage() {
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [platformFilter, setPlatformFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const loadEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (platformFilter !== 'all') params.set('platform', platformFilter);
      if (statusFilter !== 'all') params.set('status', statusFilter);
      const qs = params.toString();
      const response = await fetchWithAuth(`/webhooks/events${qs ? `?${qs}` : ''}`);
      const data = await response.json();
      setEvents(data.events || []);
    } catch (err) {
      console.error('Failed to load webhook events:', err);
    } finally {
      setLoading(false);
    }
  }, [platformFilter, statusFilter]);

  useEffect(() => {
    setLoading(true);
    loadEvents();
  }, [loadEvents]);

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Webhook Events Error">
        <PremiumShell>
          <div className="mx-auto max-w-7xl space-y-8">
            <div className="h-8 w-48 animate-pulse rounded-xl bg-slate-200" />
            <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-100" />
              ))}
            </div>
          </div>
        </PremiumShell>
      </DashboardErrorBoundary>
    );
  }

  return (
    <DashboardErrorBoundary fallbackTitle="Webhook Events Error">
      <PremiumShell>
        <motion.div
          className="mx-auto max-w-7xl space-y-8"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="flex items-center gap-3">
            <Link
              href="/settings/integrations"
              className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
              Webhook Event Log
            </h1>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 rounded-[28px] border border-slate-100/80 bg-white p-4 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
            <Filter className="h-4 w-4 text-slate-400" />
            <div>
              <label className="mr-2 text-xs font-medium text-slate-500">Platform:</label>
              <select
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 outline-none focus:border-teal-400"
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>{p === 'all' ? 'All Platforms' : p.charAt(0).toUpperCase() + p.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mr-2 text-xs font-medium text-slate-500">Status:</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 outline-none focus:border-teal-400"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
            <span className="text-xs text-slate-400">({events.length} events)</span>
          </div>

          {/* Event Table */}
          {events.length === 0 ? (
            <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
              <Webhook className="mx-auto h-10 w-10 text-slate-300" />
              <p className="mt-3 text-sm font-medium text-slate-600">No webhook events found</p>
              <p className="mt-1 text-xs text-slate-400">Events will appear here when platforms send webhook notifications</p>
            </div>
          ) : (
            <div className="rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left">
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Received</th>
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Platform</th>
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Event Type</th>
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Status</th>
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Processed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((evt) => (
                      <tr key={evt.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                        <td className="px-5 py-3 whitespace-nowrap">
                          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                            <Clock className="h-3 w-3" />
                            {formatDate(evt.received_at)}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                            {evt.platform}
                          </span>
                        </td>
                        <td className="px-5 py-3 font-mono text-xs text-slate-700">{evt.event_type}</td>
                        <td className="px-5 py-3"><StatusBadge status={evt.status} /></td>
                        <td className="px-5 py-3 text-xs text-slate-400">{formatDate(evt.processed_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </motion.div>
      </PremiumShell>
    </DashboardErrorBoundary>
  );
}
