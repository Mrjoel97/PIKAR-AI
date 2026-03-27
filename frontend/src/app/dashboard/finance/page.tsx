'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { DollarSign, Wallet, TrendingDown, Clock } from 'lucide-react';
import { usePersona } from '@/contexts/PersonaContext';
import { PersonaType } from '@/services/onboarding';
import { getDashboardSummary, DashboardSummary } from '@/services/dashboard';
import {
  getInvoices,
  getFinanceAssumptions,
  getRevenueTimeSeries,
  Invoice,
  FinanceAssumption,
  RevenueDataPoint,
} from '@/services/finance';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import { PremiumShell } from '@/components/layout/PremiumShell';

function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-56 rounded-[28px] bg-slate-200" />
        <div className="h-10 w-36 rounded-[28px] bg-slate-200" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 rounded-[28px] bg-slate-100" />
        ))}
      </div>
      <div className="h-48 rounded-[28px] bg-slate-100" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-64 rounded-[28px] bg-slate-100" />
        <div className="h-64 rounded-[28px] bg-slate-100" />
      </div>
    </div>
  );
}

export default function FinanceDashboardPage() {
  const router = useRouter();
  const { persona: ctxPersona } = usePersona();
  const persona = (ctxPersona as PersonaType) || 'startup';
  const isSolopreneur = persona === 'solopreneur';

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [assumptions, setAssumptions] = useState<FinanceAssumption[]>([]);
  const [revenue, setRevenue] = useState<RevenueDataPoint[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [summaryData, invoiceData, assumptionData, revenueData] = await Promise.all([
          getDashboardSummary(),
          getInvoices(),
          getFinanceAssumptions(),
          getRevenueTimeSeries(6),
        ]);
        setSummary(summaryData);
        setInvoices(invoiceData);
        setAssumptions(assumptionData);
        setRevenue(revenueData);
      } catch (err) {
        console.error('Failed to load finance data:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <PremiumShell>
        <LoadingSkeleton />
      </PremiumShell>
    );
  }

  const currency = summary?.finance?.currency ?? 'USD';
  const fin = summary?.finance;
  const maxRevenue = Math.max(...revenue.map((r) => r.total), 1);

  return (
    <DashboardErrorBoundary fallbackTitle="Finance Dashboard Error">
    <PremiumShell>
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Financial Dashboard</h1>
          <button
            onClick={() => router.push('/dashboard/command-center')}
            className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700"
          >
            <DollarSign className="h-4 w-4" />
            Generate Invoice
          </button>
        </div>

        {/* KPI Row */}
        <div className={`mb-8 grid gap-4 ${isSolopreneur ? 'grid-cols-2' : 'grid-cols-2 md:grid-cols-4'}`}>
          <MetricCard
            label="Revenue"
            value={formatCurrency(fin?.revenue ?? 0, currency)}
            icon={DollarSign}
            color="text-emerald-600"
            bg="bg-emerald-50"
            gradient="from-emerald-400 to-teal-500"
            delay={0}
          />
          <MetricCard
            label="Cash Position"
            value={formatCurrency(fin?.cash_position ?? 0, currency)}
            icon={Wallet}
            color="text-blue-600"
            bg="bg-blue-50"
            gradient="from-sky-400 to-blue-500"
            delay={0.05}
          />
          {!isSolopreneur && (
            <>
              <MetricCard
                label="Monthly Burn"
                value={formatCurrency(fin?.monthly_burn ?? 0, currency)}
                icon={TrendingDown}
                color="text-red-600"
                bg="bg-red-50"
                gradient="from-rose-400 to-red-500"
                delay={0.1}
              />
              <MetricCard
                label="Runway"
                value={fin?.runway_months != null ? `${fin.runway_months} mo` : 'N/A'}
                icon={Clock}
                color="text-amber-600"
                bg="bg-amber-50"
                gradient="from-amber-400 to-orange-500"
                delay={0.15}
                subtitle={fin?.runway_months != null ? 'months remaining' : undefined}
              />
            </>
          )}
        </div>

        {/* Revenue Chart */}
        <div className="mb-8 rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
          <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            Revenue Trend
          </h2>
          {revenue.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">No revenue data available yet.</p>
          ) : (
            <div className="flex items-end gap-2" style={{ height: 160 }}>
              {revenue.map((point) => {
                const heightPct = Math.max((point.total / maxRevenue) * 100, 4);
                return (
                  <div key={point.month} className="flex flex-1 flex-col items-center gap-1">
                    <span className="text-xs font-medium text-slate-600">
                      {formatCurrency(point.total, currency)}
                    </span>
                    <div
                      className="w-full rounded-t-lg bg-gradient-to-t from-teal-600 to-teal-400 transition-all"
                      style={{ height: `${heightPct}%` }}
                    />
                    <span className="text-xs text-slate-400">{point.month}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Two-column grid: Invoices + Assumptions */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Invoices */}
          <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
            <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              Recent Invoices
            </h2>
            {invoices.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">No invoices found.</p>
            ) : (
              <div className="space-y-3">
                {invoices.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex items-center justify-between rounded-2xl border border-slate-100/80 bg-slate-50/50 p-4 transition-shadow hover:shadow-md"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {inv.invoice_number ?? 'Draft'}
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {inv.client_name ?? 'No client'}
                      </p>
                      {inv.due_date && (
                        <p className="mt-0.5 text-xs text-slate-400">
                          Due {new Date(inv.due_date).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <div className="ml-4 flex flex-col items-end gap-1">
                      <span className="text-sm font-bold text-slate-900">
                        {formatCurrency(inv.amount, inv.currency ?? currency)}
                      </span>
                      <StatusBadge status={inv.status} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Assumptions */}
          <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
            <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              Finance Assumptions
            </h2>
            {assumptions.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">No active assumptions.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {assumptions.map((a) => (
                  <div key={a.id} className="flex items-center justify-between py-3">
                    <span className="text-sm text-slate-700">{a.label}</span>
                    <span className="max-w-[50%] truncate text-sm font-medium text-slate-900">
                      {JSON.stringify(a.value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </PremiumShell>
    </DashboardErrorBoundary>
  );
}
