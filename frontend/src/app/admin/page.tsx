// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

/**
 * Admin overview page — the default view at /admin.
 * Fetches /admin/overview and renders the six KPI cards returned by the
 * backend aggregator. Each card carries its own {title, value, status} so
 * one card failing on the backend degrades to "—"/neutral instead of
 * blanking the whole dashboard.
 */

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';

type CardStatus = 'ok' | 'warn' | 'error' | 'neutral';

interface OverviewCard {
  title: string;
  value: string;
  status: CardStatus;
}

interface OverviewResponse {
  cards: OverviewCard[];
}

const REFRESH_INTERVAL_MS = 60_000;

const PLACEHOLDER_CARDS: OverviewCard[] = [
  { title: 'System Status', value: '—', status: 'neutral' },
  { title: 'Active Users', value: '—', status: 'neutral' },
  { title: 'Pending Approvals', value: '—', status: 'neutral' },
  { title: 'Agent Health', value: '—', status: 'neutral' },
  { title: 'Workflow Queue', value: '—', status: 'neutral' },
  { title: 'Recent Alerts', value: '—', status: 'neutral' },
];

export default function AdminOverviewPage() {
  const [cards, setCards] = useState<OverviewCard[]>(PLACEHOLDER_CARDS);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchOverview = useCallback(async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const token = session?.access_token;
    if (!token) {
      setError('Not authenticated');
      setIsLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/admin/overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setError(`Failed to load overview (${res.status})`);
        setIsLoading(false);
        return;
      }
      const json = (await res.json()) as OverviewResponse;
      setCards(json.cards.length > 0 ? json.cards : PLACEHOLDER_CARDS);
      setError(null);
    } catch {
      setError('Failed to load overview. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [API_URL, supabase]);

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchOverview]);

  return (
    <div className="p-8">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Welcome to Pikar Admin</h1>
          <p className="mt-2 text-gray-400">
            Manage and monitor your platform from a single place.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            fetchOverview();
          }}
          className="px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh overview"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-3 bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-3">
          <p className="text-red-300 text-sm flex-1">{error}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              fetchOverview();
            }}
            className="px-3 py-1 bg-red-800 text-red-100 rounded text-xs hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards.map((card) => (
          <StatusCard
            key={card.title}
            title={card.title}
            value={isLoading ? '—' : card.value}
            status={isLoading ? 'neutral' : card.status}
          />
        ))}
      </div>
    </div>
  );
}

interface StatusCardProps {
  title: string;
  value: string;
  status: CardStatus;
}

function StatusCard({ title, value, status }: StatusCardProps) {
  const statusColors: Record<CardStatus, string> = {
    ok: 'text-green-400',
    warn: 'text-amber-400',
    error: 'text-red-400',
    neutral: 'text-gray-400',
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <p className="text-sm font-medium text-gray-400">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${statusColors[status]}`}>{value}</p>
    </div>
  );
}
