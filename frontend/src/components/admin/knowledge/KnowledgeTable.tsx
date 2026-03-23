'use client';

import { Trash2 } from 'lucide-react';

/** Shape of a single knowledge entry from the API. */
export interface KnowledgeEntry {
  id: string;
  filename: string;
  file_type: string;
  mime_type: string;
  agent_scope: string | null;
  uploaded_by: string;
  status: 'processing' | 'completed' | 'failed';
  chunk_count: number | null;
  file_size_bytes: number | null;
  created_at: string;
}

interface KnowledgeTableProps {
  entries: KnowledgeEntry[];
  totalCount: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  onDelete: (entryId: string) => void;
}

const PAGE_SIZE = 20;

/** Format bytes to human-readable string. */
function formatBytes(bytes: number | null): string {
  if (bytes === null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Status badge component. */
function StatusBadge({ status }: { status: KnowledgeEntry['status'] }) {
  const styles: Record<KnowledgeEntry['status'], string> = {
    completed: 'bg-green-500/15 text-green-400 border-green-500/30',
    processing: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    failed: 'bg-red-500/15 text-red-400 border-red-500/30',
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${styles[status]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/** Agent scope badge component. */
function ScopeBadge({ scope }: { scope: string | null }) {
  const label = scope
    ? scope.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : 'Global';
  const cls = scope
    ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
    : 'bg-gray-600/40 text-gray-300 border-gray-500/30';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}
    >
      {label}
    </span>
  );
}

/** Derive a short type label from file_type / mime_type. */
function fileTypeLabel(entry: KnowledgeEntry): string {
  if (entry.file_type) return entry.file_type.toUpperCase();
  if (entry.mime_type.startsWith('image/')) return 'IMAGE';
  if (entry.mime_type.startsWith('video/')) return 'VIDEO';
  return entry.mime_type.split('/')[1]?.toUpperCase() ?? 'FILE';
}

/** Format an ISO date string to a readable short date. */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

/**
 * KnowledgeTable renders a paginated table of knowledge base entries
 * with status badges, agent scope badges, file info, and delete actions.
 */
export function KnowledgeTable({
  entries,
  totalCount,
  currentPage,
  onPageChange,
  onDelete,
}: KnowledgeTableProps) {
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const handleDelete = (id: string, filename: string) => {
    if (window.confirm(`Delete "${filename}"? This cannot be undone.`)) {
      onDelete(id);
    }
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700 bg-gray-800/80">
              <th className="text-left px-4 py-3 text-gray-400 font-medium">
                Filename
              </th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">
                Type
              </th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">
                Agent Scope
              </th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">
                Status
              </th>
              <th className="text-right px-4 py-3 text-gray-400 font-medium">
                Chunks
              </th>
              <th className="text-right px-4 py-3 text-gray-400 font-medium">
                Size
              </th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">
                Date
              </th>
              <th className="px-4 py-3" aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="text-center py-12 text-gray-500 text-sm"
                >
                  No entries yet. Upload your first knowledge file above.
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-gray-700/50 hover:bg-gray-700/40 transition-colors"
                >
                  <td className="px-4 py-3 text-gray-200 max-w-[200px]">
                    <span className="truncate block" title={entry.filename}>
                      {entry.filename}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-mono text-gray-400">
                      {fileTypeLabel(entry)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ScopeBadge scope={entry.agent_scope} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={entry.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {entry.chunk_count ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {formatBytes(entry.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                    {formatDate(entry.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => handleDelete(entry.id, entry.filename)}
                      className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                      aria-label={`Delete ${entry.filename}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700 text-sm text-gray-400">
        <span>
          {totalCount > 0
            ? `${(currentPage - 1) * PAGE_SIZE + 1}–${Math.min(currentPage * PAGE_SIZE, totalCount)} of ${totalCount.toLocaleString()}`
            : '0 entries'}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="px-3 py-1 rounded bg-gray-700 text-gray-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors text-xs"
          >
            Previous
          </button>
          <span className="text-xs">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="px-3 py-1 rounded bg-gray-700 text-gray-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors text-xs"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
