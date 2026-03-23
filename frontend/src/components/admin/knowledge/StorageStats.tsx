'use client';

/** Format raw bytes into a human-readable string (KB / MB / GB). */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

interface StorageStatsProps {
  /** Total number of knowledge entries in the database. */
  totalEntries: number;
  /** Total number of embedding vectors stored. */
  totalEmbeddings: number;
  /** Total storage consumed in bytes. */
  storageBytes: number;
}

interface StatCardProps {
  label: string;
  value: string | number;
}

/** A single stat display card. */
function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-6 py-4 flex-1 min-w-0">
      <p className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-1">
        {label}
      </p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

/**
 * StorageStats renders three summary cards for the knowledge base:
 * total entries, total embeddings, and storage used.
 */
export function StorageStats({ totalEntries, totalEmbeddings, storageBytes }: StorageStatsProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      <StatCard label="Total Entries" value={totalEntries.toLocaleString()} />
      <StatCard label="Total Embeddings" value={totalEmbeddings.toLocaleString()} />
      <StatCard label="Storage Used" value={formatBytes(storageBytes)} />
    </div>
  );
}
