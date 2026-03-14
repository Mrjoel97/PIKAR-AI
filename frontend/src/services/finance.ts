import { createClient } from '@/lib/supabase/client';

// Types
export interface Invoice {
  id: string;
  user_id: string;
  invoice_number: string | null;
  client_name: string | null;
  client_email: string | null;
  amount: number;
  currency: string;
  status: string; // draft, sent, paid, overdue, void
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinanceAssumption {
  id: string;
  assumption_type: string;
  key: string;
  label: string;
  value: unknown; // JSONB
  is_active: boolean;
  created_at: string;
}

export interface RevenueDataPoint {
  month: string;
  total: number;
}

export async function getInvoices(): Promise<Invoice[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('invoices')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50);
  if (error) throw error;
  return (data ?? []) as Invoice[];
}

export async function getFinanceAssumptions(): Promise<FinanceAssumption[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('finance_assumptions_ledger')
    .select('*')
    .eq('is_active', true)
    .order('created_at', { ascending: false });
  if (error) throw error;
  return (data ?? []) as FinanceAssumption[];
}

export async function getRevenueTimeSeries(months: number = 6): Promise<RevenueDataPoint[]> {
  const supabase = createClient();
  const since = new Date();
  since.setMonth(since.getMonth() - months);

  const { data, error } = await supabase
    .from('payment_transactions')
    .select('amount, created_at')
    .eq('status', 'succeeded')
    .gte('created_at', since.toISOString())
    .order('created_at', { ascending: true });

  if (error) throw error;

  // Group by month
  const byMonth: Record<string, number> = {};
  for (const row of data ?? []) {
    const d = new Date(row.created_at);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    byMonth[key] = (byMonth[key] ?? 0) + Number(row.amount);
  }

  return Object.entries(byMonth)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, total]) => ({ month, total }));
}
