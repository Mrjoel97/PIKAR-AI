-- Migration: Create financial_records table for revenue tracking
-- Created: 2026-02-15
-- Description: Stores financial transaction records for revenue analytics

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the financial_records table
CREATE TABLE IF NOT EXISTS financial_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Transaction details
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('revenue', 'expense', 'refund', 'adjustment')),
    amount DECIMAL(15, 2) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Categorization
    category VARCHAR(100),
    subcategory VARCHAR(100),
    description TEXT,
    
    -- Source tracking
    source_type VARCHAR(50), -- e.g., 'stripe', 'manual', 'api', 'import'
    source_id VARCHAR(255),  -- External reference ID
    
    -- Metadata
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    
    -- Constraints
    CONSTRAINT positive_amount CHECK (amount >= 0)
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_financial_records_user_id ON financial_records(user_id);
CREATE INDEX IF NOT EXISTS idx_financial_records_type ON financial_records(transaction_type);
CREATE INDEX IF NOT EXISTS idx_financial_records_date ON financial_records(transaction_date);
CREATE INDEX IF NOT EXISTS idx_financial_records_user_type_date ON financial_records(user_id, transaction_type, transaction_date);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_financial_records_updated_at ON financial_records;
CREATE TRIGGER update_financial_records_updated_at
    BEFORE UPDATE ON financial_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE financial_records ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own financial records
CREATE POLICY "Users can view own financial records"
    ON financial_records
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- RLS Policy: Users can insert their own financial records
CREATE POLICY "Users can insert own financial records"
    ON financial_records
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- RLS Policy: Users can update their own financial records
CREATE POLICY "Users can update own financial records"
    ON financial_records
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- RLS Policy: Users can delete their own financial records
CREATE POLICY "Users can delete own financial records"
    ON financial_records
    FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- Create view for revenue summary by period
CREATE OR REPLACE VIEW revenue_summary AS
SELECT 
    user_id,
    DATE_TRUNC('month', transaction_date) as period,
    currency,
    SUM(amount) as total_revenue,
    COUNT(*) as transaction_count,
    MIN(transaction_date) as first_transaction,
    MAX(transaction_date) as last_transaction
FROM financial_records
WHERE transaction_type = 'revenue'
GROUP BY user_id, DATE_TRUNC('month', transaction_date), currency
ORDER BY period DESC;

-- Create function to get revenue stats for a user
CREATE OR REPLACE FUNCTION get_revenue_stats(
    p_user_id UUID,
    p_period TEXT DEFAULT 'current_month'
)
RETURNS TABLE (
    revenue DECIMAL,
    currency VARCHAR,
    transaction_count BIGINT,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ
) AS $$
DECLARE
    v_start_date TIMESTAMPTZ;
    v_end_date TIMESTAMPTZ;
BEGIN
    -- Calculate date range based on period
    CASE p_period
        WHEN 'current_month' THEN
            v_start_date := DATE_TRUNC('month', NOW());
            v_end_date := DATE_TRUNC('month', NOW()) + INTERVAL '1 month' - INTERVAL '1 second';
        WHEN 'last_month' THEN
            v_start_date := DATE_TRUNC('month', NOW() - INTERVAL '1 month');
            v_end_date := DATE_TRUNC('month', NOW()) - INTERVAL '1 second';
        WHEN 'current_quarter' THEN
            v_start_date := DATE_TRUNC('quarter', NOW());
            v_end_date := DATE_TRUNC('quarter', NOW()) + INTERVAL '3 months' - INTERVAL '1 second';
        WHEN 'current_year' THEN
            v_start_date := DATE_TRUNC('year', NOW());
            v_end_date := DATE_TRUNC('year', NOW()) + INTERVAL '1 year' - INTERVAL '1 second';
        WHEN 'all_time' THEN
            v_start_date := '1970-01-01'::TIMESTAMPTZ;
            v_end_date := NOW();
        ELSE
            v_start_date := DATE_TRUNC('month', NOW());
            v_end_date := DATE_TRUNC('month', NOW()) + INTERVAL '1 month' - INTERVAL '1 second';
    END CASE;

    RETURN QUERY
    SELECT 
        COALESCE(SUM(fr.amount), 0) as revenue,
        'USD'::VARCHAR as currency,
        COUNT(*) as transaction_count,
        v_start_date as period_start,
        v_end_date as period_end
    FROM financial_records fr
    WHERE fr.user_id = p_user_id
        AND fr.transaction_type = 'revenue'
        AND fr.transaction_date >= v_start_date
        AND fr.transaction_date <= v_end_date;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT ALL ON financial_records TO authenticated;
GRANT ALL ON revenue_summary TO authenticated;
GRANT EXECUTE ON FUNCTION get_revenue_stats(UUID, TEXT) TO authenticated;

-- Add helpful comments
COMMENT ON TABLE financial_records IS 'Stores financial transaction records for revenue and expense tracking';
COMMENT ON COLUMN financial_records.transaction_type IS 'Type of transaction: revenue, expense, refund, or adjustment';
COMMENT ON COLUMN financial_records.amount IS 'Transaction amount (always positive, use transaction_type to indicate direction)';
COMMENT ON COLUMN financial_records.source_type IS 'Origin of the transaction: stripe, manual, api, import, etc.';
COMMENT ON VIEW revenue_summary IS 'Aggregated revenue data by month and currency';
COMMENT ON FUNCTION get_revenue_stats IS 'Returns revenue statistics for a user for a given period';
