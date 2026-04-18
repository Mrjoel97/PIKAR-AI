'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { StorageStats } from '@/components/admin/knowledge/StorageStats';
import { AgentKnowledgeCards } from '@/components/admin/knowledge/AgentKnowledgeCards';
import { KnowledgeTable } from '@/components/admin/knowledge/KnowledgeTable';
import type { KnowledgeEntry } from '@/components/admin/knowledge/KnowledgeTable';
import { UploadPanel } from '@/components/admin/knowledge/UploadPanel';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const PAGE_SIZE = 20;

/** Shape of the /admin/knowledge/stats response. */
interface StatsData {
  total_entries: number;
  total_embeddings: number;
  by_agent: Record<string, number>;
  storage_bytes: number;
}

/**
 * KnowledgePage renders /admin/knowledge — the admin knowledge base
 * management dashboard with storage stats, per-agent cards, file upload,
 * and a paginated upload history table.
 */
export default function KnowledgePage() {
  const supabase = createClient();

  const [token, setToken] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const [stats, setStats] = useState<StatsData | null>(null);
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

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
        setAuthError('Not authenticated. Please sign in to access knowledge management.');
        return;
      }

      setToken(session.access_token);
    };

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, [supabase]);

  // ─── Fetch stats ───────────────────────────────────────────────────────────

  const fetchStats = useCallback(async (currentToken: string) => {
    try {
      const res = await fetch(`${API_URL}/admin/knowledge/stats`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      });
      if (res.ok) {
        setStats(await res.json() as StatsData);
      }
    } catch {
      // Stats are non-critical — silent fail, cards show nothing
    }
  }, []);

  // ─── Fetch entries ─────────────────────────────────────────────────────────

  const fetchEntries = useCallback(async (currentToken: string, pageNum: number) => {
    try {
      const offset = (pageNum - 1) * PAGE_SIZE;
      const res = await fetch(
        `${API_URL}/admin/knowledge/entries?limit=${PAGE_SIZE}&offset=${offset}`,
        { headers: { Authorization: `Bearer ${currentToken}` } },
      );
      if (res.ok) {
        const data = await res.json() as { data: KnowledgeEntry[]; count: number };
        setEntries(data.data);
        setTotalCount(data.count);
      }
    } catch {
      // Entries fetch failed — table stays empty
    }
  }, []);

  // ─── Initial load ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([fetchStats(token), fetchEntries(token, page)]).finally(() =>
      setLoading(false),
    );
  }, [token, page, fetchStats, fetchEntries]);

  // ─── Handlers ──────────────────────────────────────────────────────────────

  const handleUploadComplete = useCallback(() => {
    if (!token) return;
    fetchStats(token);
    fetchEntries(token, page);
  }, [token, page, fetchStats, fetchEntries]);

  const handleDelete = useCallback(
    async (entryId: string) => {
      if (!token) return;
      try {
        const res = await fetch(`${API_URL}/admin/knowledge/entries/${entryId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          fetchStats(token);
          fetchEntries(token, page);
        }
      } catch {
        // Delete failed — no-op, table stays as-is
      }
    },
    [token, page, fetchStats, fetchEntries],
  );

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  // ─── Render ────────────────────────────────────────────────────────────────

  if (authError) {
    return (
      <div className="p-8">
        <p className="text-red-400 text-sm">{authError}</p>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Knowledge Base</h1>
        <p className="text-sm text-gray-400 mt-1">
          Manage agent training data — upload documents, images, and videos to enhance agent capabilities.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full" />
          <span className="ml-3 text-gray-400 text-sm">Loading knowledge base…</span>
        </div>
      ) : (
        <>
          {/* Storage stats */}
          <StorageStats
            totalEntries={stats?.total_entries ?? 0}
            totalEmbeddings={stats?.total_embeddings ?? 0}
            storageBytes={stats?.storage_bytes ?? 0}
          />

          {/* Upload panel + agent cards side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <UploadPanel
              token={token ?? ''}
              onUploadComplete={handleUploadComplete}
            />
            <AgentKnowledgeCards byAgent={stats?.by_agent ?? {}} />
          </div>

          {/* Upload history table */}
          <div>
            <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wide mb-3">
              Upload History
            </h2>
            <KnowledgeTable
              entries={entries}
              totalCount={totalCount}
              currentPage={page}
              onPageChange={handlePageChange}
              onDelete={handleDelete}
            />
          </div>
        </>
      )}
    </div>
  );
}
