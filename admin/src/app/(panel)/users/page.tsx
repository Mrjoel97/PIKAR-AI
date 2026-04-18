'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
  type PaginationState,
} from '@tanstack/react-table';
import { createClient } from '@/lib/supabase/client';
import { Search, ChevronLeft, ChevronRight, Users } from 'lucide-react';

/** User row returned by GET /admin/users */
interface UserRow {
  id: string;
  email: string;
  persona: string | null;
  agent_name: string | null;
  created_at: string;
  banned_until: string | null;
  onboarding_completed: boolean;
}

interface UsersResponse {
  users: UserRow[];
  total: number;
  page: number;
  page_size: number;
}

/** Colored badge for persona values */
const personaBadgeClass: Record<string, string> = {
  solopreneur: 'bg-blue-900 text-blue-300',
  startup: 'bg-green-900 text-green-300',
  sme: 'bg-amber-900 text-amber-300',
  enterprise: 'bg-purple-900 text-purple-300',
};

/** Returns true when the user is currently suspended */
function isSuspended(bannedUntil: string | null): boolean {
  if (!bannedUntil) return false;
  return new Date(bannedUntil) > new Date();
}

/** Format ISO date string as YYYY-MM-DD */
function formatDate(iso: string): string {
  return iso.split('T')[0] ?? iso;
}

const PAGE_SIZE = 25;

/**
 * UsersPage renders the /admin/users table with search, persona/status filters,
 * server-side pagination via TanStack Table, and row-click navigation.
 */
export default function UsersPage() {
  const router = useRouter();
  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Table data
  const [data, setData] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Filter state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [personaFilter, setPersonaFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Pagination state
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  });

  // Debounce search input 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPagination((prev) => ({ ...prev, pageIndex: 0 }));
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Reset page when filters change
  useEffect(() => {
    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
  }, [personaFilter, statusFilter]);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        return;
      }

      const params = new URLSearchParams({
        page: String(pagination.pageIndex + 1),
        page_size: String(pagination.pageSize),
      });
      if (debouncedSearch) params.set('search', debouncedSearch);
      if (personaFilter) params.set('persona', personaFilter);
      if (statusFilter) params.set('status', statusFilter);

      const res = await fetch(`${API_URL}/admin/users?${params.toString()}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load users (${res.status})`);
        return;
      }

      const json = (await res.json()) as UsersResponse;
      setData(json.users ?? []);
      setTotal(json.total ?? 0);
    } catch {
      setFetchError('Failed to load users. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL, pagination.pageIndex, pagination.pageSize, debouncedSearch, personaFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Column definitions
  const columns: ColumnDef<UserRow>[] = [
    {
      id: 'email',
      header: 'Email',
      cell: ({ row }) => (
        <span className="text-gray-100 font-medium truncate block max-w-[220px]">
          {row.original.email}
        </span>
      ),
    },
    {
      id: 'persona',
      header: 'Persona',
      cell: ({ row }) => {
        const p = row.original.persona;
        if (!p) return <span className="text-gray-500 text-xs">—</span>;
        return (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
              personaBadgeClass[p] ?? 'bg-gray-700 text-gray-300'
            }`}
          >
            {p}
          </span>
        );
      },
    },
    {
      id: 'signup_date',
      header: 'Signup Date',
      cell: ({ row }) => (
        <span className="text-gray-400 text-sm">{formatDate(row.original.created_at)}</span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const suspended = isSuspended(row.original.banned_until);
        return suspended ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-900 text-red-300">
            Suspended
          </span>
        ) : (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-900 text-green-300">
            Active
          </span>
        );
      },
    },
  ];

  const table = useReactTable({
    data,
    columns,
    rowCount: total,
    state: { pagination },
    onPaginationChange: setPagination,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
  });

  const pageStart = pagination.pageIndex * pagination.pageSize + 1;
  const pageEnd = Math.min((pagination.pageIndex + 1) * pagination.pageSize, total);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Users size={24} className="text-gray-400" />
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Users</h1>
          {total > 0 && (
            <p className="mt-0.5 text-sm text-gray-400">{total} total users</p>
          )}
        </div>
      </div>

      {/* Search + filters */}
      <div className="flex flex-wrap items-center gap-3 mb-5 bg-gray-900 border border-gray-700 rounded-xl p-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by email..."
            className="w-full bg-gray-800 text-gray-100 text-sm rounded-lg pl-9 pr-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500 placeholder-gray-500"
          />
        </div>

        {/* Persona filter */}
        <div className="flex items-center gap-2">
          <label htmlFor="persona-filter" className="text-sm text-gray-400">
            Persona
          </label>
          <select
            id="persona-filter"
            value={personaFilter}
            onChange={(e) => setPersonaFilter(e.target.value)}
            className="bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All</option>
            <option value="solopreneur">Solopreneur</option>
            <option value="startup">Startup</option>
            <option value="sme">SME</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2">
          <label htmlFor="status-filter" className="text-sm text-gray-400">
            Status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>

      {/* Content area */}
      {isLoading && data.length === 0 ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
        </div>
      ) : fetchError ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-400 text-sm">{fetchError}</p>
          <button
            type="button"
            onClick={() => fetchUsers()}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      ) : data.length === 0 ? (
        <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
          No users found.
        </div>
      ) : (
        <>
          {/* Loading overlay */}
          {isLoading && (
            <div className="mb-2 flex items-center gap-2 text-xs text-gray-500">
              <div className="animate-spin rounded-full h-3 w-3 border border-indigo-500 border-t-transparent" />
              Loading...
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-gray-700">
            <table className="w-full text-sm">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="bg-gray-800 text-gray-400 text-left">
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-4 py-3 font-medium">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => router.push(`/admin/users/${row.original.id}`)}
                    className="border-t border-gray-700 hover:bg-gray-800/60 transition-colors cursor-pointer"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
            <span>
              Showing {pageStart}–{pageEnd} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-600 transition-colors"
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-600 transition-colors"
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
