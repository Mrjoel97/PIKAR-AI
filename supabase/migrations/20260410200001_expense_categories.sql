-- Expense Categories Reference Table & Financial Records Index
-- Phase 60-02: Automatic Stripe expense categorization
--
-- Creates a reference table of business expense categories and adds
-- a composite index on financial_records for efficient category grouping.

-- 1. Reference table for expense categories
CREATE TABLE IF NOT EXISTS public.expense_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.expense_categories IS 'Reference table of business expense categories for Stripe transaction classification';

-- 2. Seed standard categories
INSERT INTO public.expense_categories (name, display_name, description, sort_order) VALUES
    ('revenue',              'Revenue',              'Income from charges and payments',               1),
    ('marketing',            'Marketing',            'Advertising, email marketing, SEO tools',        2),
    ('saas_tools',           'SaaS Tools',           'Software subscriptions and productivity tools',  3),
    ('infrastructure',       'Infrastructure',       'Cloud hosting, CDN, monitoring services',        4),
    ('payroll',              'Payroll',               'Salaries, wages, and payroll processing',        5),
    ('professional_services','Professional Services', 'Legal, accounting, and consulting fees',         6),
    ('office',               'Office',                'Office space, supplies, and utilities',          7),
    ('travel',               'Travel',                'Flights, hotels, rideshare, and travel expenses',8),
    ('cogs',                 'Cost of Goods Sold',    'Manufacturing, materials, shipping, fulfillment',9),
    ('taxes_fees',           'Taxes & Fees',          'Stripe fees, taxes, and processing charges',    10),
    ('transfers',            'Transfers',             'Bank payouts and fund transfers',               11),
    ('other',                'Other',                 'Uncategorized transactions',                    12)
ON CONFLICT (name) DO NOTHING;

-- 3. RLS policies
ALTER TABLE public.expense_categories ENABLE ROW LEVEL SECURITY;

-- Read access for all authenticated users
CREATE POLICY "expense_categories_select_authenticated"
    ON public.expense_categories
    FOR SELECT
    TO authenticated
    USING (true);

-- Full access for service_role (admin operations)
CREATE POLICY "expense_categories_all_service_role"
    ON public.expense_categories
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 4. Index on financial_records.category for efficient grouping queries
CREATE INDEX IF NOT EXISTS idx_financial_records_category
    ON public.financial_records(user_id, category)
    WHERE category IS NOT NULL;
