'use client';

import React from 'react';

interface DashboardSkeletonProps {
  rows?: number;
  columns?: number;
  showMetricCards?: boolean;
}

function SkeletonCard() {
  return (
    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)] animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0 space-y-2">
          <div className="h-3 w-20 rounded bg-slate-200" />
          <div className="h-7 w-28 rounded bg-slate-200" />
          <div className="h-3 w-16 rounded bg-slate-100" />
        </div>
        <div className="flex-shrink-0 rounded-2xl bg-slate-200 p-3 h-11 w-11" />
      </div>
    </div>
  );
}

function SkeletonSection() {
  return (
    <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)] animate-pulse">
      <div className="h-4 w-32 rounded bg-slate-200 mb-4" />
      <div className="space-y-3">
        <div className="h-3 w-full rounded bg-slate-100" />
        <div className="h-3 w-3/4 rounded bg-slate-100" />
        <div className="h-3 w-1/2 rounded bg-slate-100" />
      </div>
    </div>
  );
}

export default function DashboardSkeleton({
  rows = 2,
  columns = 2,
  showMetricCards = true,
}: DashboardSkeletonProps) {
  return (
    <div className="space-y-6">
      {showMetricCards && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={`metric-${i}`} />
          ))}
        </div>
      )}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={`row-${r}`} className={`grid gap-4 grid-cols-1 ${columns > 1 ? `lg:grid-cols-${columns}` : ''}`}>
          {Array.from({ length: columns }).map((_, c) => (
            <SkeletonSection key={`section-${r}-${c}`} />
          ))}
        </div>
      ))}
    </div>
  );
}
