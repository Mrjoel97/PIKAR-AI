import { fetchWithAuth } from './api';

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
  const response = await fetchWithAuth('/finance/invoices');
  return response.json();
}

export async function getFinanceAssumptions(): Promise<FinanceAssumption[]> {
  const response = await fetchWithAuth('/finance/assumptions');
  return response.json();
}

export async function getRevenueTimeSeries(months: number = 6): Promise<RevenueDataPoint[]> {
  const response = await fetchWithAuth(`/finance/revenue-timeseries?months=${months}`);
  return response.json();
}
