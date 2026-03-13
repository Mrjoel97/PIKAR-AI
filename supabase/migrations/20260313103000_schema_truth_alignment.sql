-- Migration: 20260313103000_schema_truth_alignment.sql
-- Description: Canonicalize out-of-band schema owners and add canonical tables
--              for runtime analytics and journey-tracking features.

-- -----------------------------------------------------------------------------
-- financial_records
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.financial_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (
        transaction_type IN ('revenue', 'expense', 'refund', 'adjustment')
    ),
    amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    category TEXT,
    subcategory TEXT,
    description TEXT,
    source_type TEXT,
    source_id TEXT,
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

ALTER TABLE public.financial_records
    ADD COLUMN IF NOT EXISTS transaction_type TEXT,
    ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD',
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS subcategory TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS source_type TEXT,
    ADD COLUMN IF NOT EXISTS source_id TEXT,
    ADD COLUMN IF NOT EXISTS transaction_date TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

UPDATE public.financial_records
SET
    currency = COALESCE(currency, 'USD'),
    transaction_date = COALESCE(transaction_date, recorded_at, created_at, now()),
    recorded_at = COALESCE(recorded_at, created_at, now()),
    metadata = COALESCE(metadata, '{}'::jsonb),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now())
WHERE currency IS NULL
   OR transaction_date IS NULL
   OR recorded_at IS NULL
   OR metadata IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE public.financial_records
    ALTER COLUMN currency SET DEFAULT 'USD',
    ALTER COLUMN currency SET NOT NULL,
    ALTER COLUMN transaction_date SET DEFAULT now(),
    ALTER COLUMN transaction_date SET NOT NULL,
    ALTER COLUMN recorded_at SET DEFAULT now(),
    ALTER COLUMN recorded_at SET NOT NULL,
    ALTER COLUMN metadata SET DEFAULT '{}'::jsonb,
    ALTER COLUMN metadata SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_financial_records_user_transaction_date
    ON public.financial_records(user_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_financial_records_transaction_type
    ON public.financial_records(transaction_type);
CREATE INDEX IF NOT EXISTS idx_financial_records_user_transaction_type_date
    ON public.financial_records(user_id, transaction_type, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_financial_records_created_by
    ON public.financial_records(created_by);

ALTER TABLE public.financial_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own financial records" ON public.financial_records;
CREATE POLICY "Users can view own financial records"
    ON public.financial_records
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can insert own financial records" ON public.financial_records;
CREATE POLICY "Users can insert own financial records"
    ON public.financial_records
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update own financial records" ON public.financial_records;
CREATE POLICY "Users can update own financial records"
    ON public.financial_records
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete own financial records" ON public.financial_records;
CREATE POLICY "Users can delete own financial records"
    ON public.financial_records
    FOR DELETE TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Service role manages financial records" ON public.financial_records;
CREATE POLICY "Service role manages financial records"
    ON public.financial_records
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_financial_records_updated_at ON public.financial_records;
CREATE TRIGGER update_financial_records_updated_at
    BEFORE UPDATE ON public.financial_records
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE OR REPLACE VIEW public.revenue_summary AS
SELECT
    user_id,
    date_trunc('month', transaction_date) AS period,
    currency,
    SUM(amount) AS total_revenue,
    COUNT(*) AS transaction_count,
    MIN(transaction_date) AS first_transaction,
    MAX(transaction_date) AS last_transaction
FROM public.financial_records
WHERE transaction_type = 'revenue'
GROUP BY user_id, date_trunc('month', transaction_date), currency;

ALTER VIEW public.revenue_summary SET (security_invoker = true);

CREATE OR REPLACE FUNCTION public.get_revenue_stats(
    p_user_id UUID,
    p_period TEXT DEFAULT 'current_month'
)
RETURNS TABLE (
    revenue NUMERIC,
    currency TEXT,
    transaction_count BIGINT,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_start_date TIMESTAMPTZ;
    v_end_date TIMESTAMPTZ;
BEGIN
    CASE p_period
        WHEN 'current_month' THEN
            v_start_date := date_trunc('month', now());
            v_end_date := date_trunc('month', now()) + INTERVAL '1 month' - INTERVAL '1 second';
        WHEN 'last_month' THEN
            v_start_date := date_trunc('month', now() - INTERVAL '1 month');
            v_end_date := date_trunc('month', now()) - INTERVAL '1 second';
        WHEN 'current_quarter' THEN
            v_start_date := date_trunc('quarter', now());
            v_end_date := date_trunc('quarter', now()) + INTERVAL '3 months' - INTERVAL '1 second';
        WHEN 'current_year' THEN
            v_start_date := date_trunc('year', now());
            v_end_date := date_trunc('year', now()) + INTERVAL '1 year' - INTERVAL '1 second';
        WHEN 'all_time' THEN
            v_start_date := '1970-01-01'::timestamptz;
            v_end_date := now();
        ELSE
            v_start_date := date_trunc('month', now());
            v_end_date := date_trunc('month', now()) + INTERVAL '1 month' - INTERVAL '1 second';
    END CASE;

    RETURN QUERY
    SELECT
        COALESCE(SUM(fr.amount), 0) AS revenue,
        COALESCE(MAX(fr.currency), 'USD') AS currency,
        COUNT(*) AS transaction_count,
        v_start_date AS period_start,
        v_end_date AS period_end
    FROM public.financial_records fr
    WHERE fr.user_id = p_user_id
      AND fr.transaction_type = 'revenue'
      AND fr.transaction_date >= v_start_date
      AND fr.transaction_date <= v_end_date;
END;
$$;

ALTER FUNCTION public.get_revenue_stats(UUID, TEXT) SET search_path = public;

COMMENT ON TABLE public.financial_records IS 'Canonical financial ledger for revenue, expense, refund, and adjustment records.';

-- -----------------------------------------------------------------------------
-- mcp_integration_templates and user_mcp_integrations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.mcp_integration_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon_url TEXT,
    category TEXT NOT NULL DEFAULT 'other',
    required_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    optional_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    test_endpoint TEXT,
    docs_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.mcp_integration_templates
    ADD COLUMN IF NOT EXISTS icon_url TEXT,
    ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS required_fields JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS optional_fields JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS test_endpoint TEXT,
    ADD COLUMN IF NOT EXISTS docs_url TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

UPDATE public.mcp_integration_templates
SET
    category = COALESCE(category, 'other'),
    required_fields = COALESCE(required_fields, '[]'::jsonb),
    optional_fields = COALESCE(optional_fields, '[]'::jsonb),
    is_active = COALESCE(is_active, true),
    created_at = COALESCE(created_at, now())
WHERE category IS NULL
   OR required_fields IS NULL
   OR optional_fields IS NULL
   OR is_active IS NULL
   OR created_at IS NULL;

ALTER TABLE public.mcp_integration_templates
    ALTER COLUMN category SET DEFAULT 'other',
    ALTER COLUMN category SET NOT NULL,
    ALTER COLUMN required_fields SET DEFAULT '[]'::jsonb,
    ALTER COLUMN required_fields SET NOT NULL,
    ALTER COLUMN optional_fields SET DEFAULT '[]'::jsonb,
    ALTER COLUMN optional_fields SET NOT NULL,
    ALTER COLUMN is_active SET DEFAULT true,
    ALTER COLUMN is_active SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE public.mcp_integration_templates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view active integration templates" ON public.mcp_integration_templates;
CREATE POLICY "Authenticated users can view active integration templates"
    ON public.mcp_integration_templates
    FOR SELECT TO authenticated
    USING (is_active = true);

DROP POLICY IF EXISTS "Service role manages integration templates" ON public.mcp_integration_templates;
CREATE POLICY "Service role manages integration templates"
    ON public.mcp_integration_templates
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

INSERT INTO public.mcp_integration_templates (
    id,
    name,
    description,
    category,
    required_fields,
    optional_fields,
    docs_url
) VALUES
    (
        'supabase',
        'Supabase',
        'Database, Auth, and Storage',
        'database',
        '[{"key":"url","label":"Project URL","type":"url","placeholder":"https://xxx.supabase.co"},{"key":"anon_key","label":"Anon/Public Key","type":"secret","placeholder":"eyJ..."},{"key":"service_role_key","label":"Service Role Key","type":"secret","placeholder":"eyJ..."}]'::jsonb,
        '[]'::jsonb,
        'https://supabase.com/docs'
    ),
    (
        'resend',
        'Resend',
        'Email API for developers',
        'email',
        '[{"key":"api_key","label":"API Key","type":"secret","placeholder":"re_..."}]'::jsonb,
        '[{"key":"from_email","label":"Default From Email","type":"email","placeholder":"hello@yourdomain.com"}]'::jsonb,
        'https://resend.com/docs'
    ),
    (
        'slack',
        'Slack',
        'Team messaging and notifications',
        'communication',
        '[{"key":"webhook_url","label":"Webhook URL","type":"url","placeholder":"https://hooks.slack.com/..."}]'::jsonb,
        '[{"key":"bot_token","label":"Bot Token (optional)","type":"secret","placeholder":"xoxb-..."}]'::jsonb,
        'https://api.slack.com/docs'
    ),
    (
        'notion',
        'Notion',
        'Workspace and documentation',
        'productivity',
        '[{"key":"api_key","label":"Integration Token","type":"secret","placeholder":"secret_..."}]'::jsonb,
        '[]'::jsonb,
        'https://developers.notion.com'
    ),
    (
        'airtable',
        'Airtable',
        'Spreadsheet database',
        'database',
        '[{"key":"api_key","label":"API Key","type":"secret","placeholder":"pat..."},{"key":"base_id","label":"Base ID","type":"text","placeholder":"app..."}]'::jsonb,
        '[]'::jsonb,
        'https://airtable.com/developers/web/api'
    ),
    (
        'hubspot',
        'HubSpot',
        'CRM and marketing',
        'crm',
        '[{"key":"api_key","label":"Private App Token","type":"secret","placeholder":"pat-..."}]'::jsonb,
        '[]'::jsonb,
        'https://developers.hubspot.com'
    ),
    (
        'stripe',
        'Stripe',
        'Payments and billing',
        'payments',
        '[{"key":"secret_key","label":"Secret Key","type":"secret","placeholder":"sk_..."}]'::jsonb,
        '[{"key":"webhook_secret","label":"Webhook Secret","type":"secret","placeholder":"whsec_..."}]'::jsonb,
        'https://stripe.com/docs/api'
    ),
    (
        'openai',
        'OpenAI',
        'AI models and APIs',
        'ai',
        '[{"key":"api_key","label":"API Key","type":"secret","placeholder":"sk-..."}]'::jsonb,
        '[{"key":"org_id","label":"Organization ID","type":"text","placeholder":"org-..."}]'::jsonb,
        'https://platform.openai.com/docs'
    ),
    (
        'custom',
        'Custom Integration',
        'Configure any API manually',
        'other',
        '[{"key":"base_url","label":"Base URL","type":"url","placeholder":"https://api.example.com"}]'::jsonb,
        '[{"key":"api_key","label":"API Key","type":"secret"},{"key":"headers","label":"Custom Headers (JSON)","type":"json"}]'::jsonb,
        NULL
    )
ON CONFLICT (id) DO UPDATE
SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    required_fields = EXCLUDED.required_fields,
    optional_fields = EXCLUDED.optional_fields,
    docs_url = EXCLUDED.docs_url,
    is_active = true;

CREATE TABLE IF NOT EXISTS public.user_mcp_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    integration_type TEXT NOT NULL,
    display_name TEXT,
    config_encrypted TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT false,
    last_tested_at TIMESTAMPTZ,
    test_status TEXT,
    test_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.user_mcp_integrations
    ADD COLUMN IF NOT EXISTS display_name TEXT,
    ADD COLUMN IF NOT EXISTS config_encrypted TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS test_status TEXT,
    ADD COLUMN IF NOT EXISTS test_error TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.user_mcp_integrations
SET
    display_name = COALESCE(display_name, integration_type),
    is_active = COALESCE(is_active, false),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now())
WHERE display_name IS NULL
   OR is_active IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE public.user_mcp_integrations
    ALTER COLUMN display_name SET NOT NULL,
    ALTER COLUMN is_active SET DEFAULT false,
    ALTER COLUMN is_active SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'user_mcp_integrations_test_status_check'
          AND conrelid = 'public.user_mcp_integrations'::regclass
    ) THEN
        ALTER TABLE public.user_mcp_integrations
            ADD CONSTRAINT user_mcp_integrations_test_status_check
            CHECK (test_status IN ('success', 'failed', 'pending') OR test_status IS NULL);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'user_mcp_integrations_user_type_display_name_key'
          AND conrelid = 'public.user_mcp_integrations'::regclass
    ) THEN
        ALTER TABLE public.user_mcp_integrations
            ADD CONSTRAINT user_mcp_integrations_user_type_display_name_key
            UNIQUE (user_id, integration_type, display_name);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_mcp_integrations_user_id
    ON public.user_mcp_integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mcp_integrations_type
    ON public.user_mcp_integrations(integration_type);
CREATE INDEX IF NOT EXISTS idx_user_mcp_integrations_active
    ON public.user_mcp_integrations(is_active)
    WHERE is_active = true;

ALTER TABLE public.user_mcp_integrations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own MCP integrations" ON public.user_mcp_integrations;
CREATE POLICY "Users can view their own MCP integrations"
    ON public.user_mcp_integrations
    FOR SELECT TO authenticated
    USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can insert their own MCP integrations" ON public.user_mcp_integrations;
CREATE POLICY "Users can insert their own MCP integrations"
    ON public.user_mcp_integrations
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can update their own MCP integrations" ON public.user_mcp_integrations;
CREATE POLICY "Users can update their own MCP integrations"
    ON public.user_mcp_integrations
    FOR UPDATE TO authenticated
    USING (auth.uid()::text = user_id)
    WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can delete their own MCP integrations" ON public.user_mcp_integrations;
CREATE POLICY "Users can delete their own MCP integrations"
    ON public.user_mcp_integrations
    FOR DELETE TO authenticated
    USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Service role manages MCP integrations" ON public.user_mcp_integrations;
CREATE POLICY "Service role manages MCP integrations"
    ON public.user_mcp_integrations
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_user_mcp_integrations_updated_at ON public.user_mcp_integrations;
CREATE TRIGGER update_user_mcp_integrations_updated_at
    BEFORE UPDATE ON public.user_mcp_integrations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- analytics tables
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    category TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.analytics_events
    ADD COLUMN IF NOT EXISTS properties JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

UPDATE public.analytics_events
SET
    properties = COALESCE(properties, '{}'::jsonb),
    created_at = COALESCE(created_at, now())
WHERE properties IS NULL
   OR created_at IS NULL;

ALTER TABLE public.analytics_events
    ALTER COLUMN properties SET DEFAULT '{}'::jsonb,
    ALTER COLUMN properties SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_analytics_events_user_created_at
    ON public.analytics_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_category
    ON public.analytics_events(category);
CREATE INDEX IF NOT EXISTS idx_analytics_events_name
    ON public.analytics_events(event_name);

ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own analytics events" ON public.analytics_events;
CREATE POLICY "Users can manage their own analytics events"
    ON public.analytics_events
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages analytics events" ON public.analytics_events;
CREATE POLICY "Service role manages analytics events"
    ON public.analytics_events
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE TABLE IF NOT EXISTS public.analytics_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    report_type TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.analytics_reports
    ADD COLUMN IF NOT EXISTS data JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.analytics_reports
SET
    data = COALESCE(data, '{}'::jsonb),
    status = COALESCE(status, 'draft'),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now())
WHERE data IS NULL
   OR status IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE public.analytics_reports
    ALTER COLUMN data SET DEFAULT '{}'::jsonb,
    ALTER COLUMN data SET NOT NULL,
    ALTER COLUMN status SET DEFAULT 'draft',
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'analytics_reports_status_check'
          AND conrelid = 'public.analytics_reports'::regclass
    ) THEN
        ALTER TABLE public.analytics_reports
            ADD CONSTRAINT analytics_reports_status_check
            CHECK (status IN ('draft', 'final', 'archived', 'failed'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_analytics_reports_user_created_at
    ON public.analytics_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_reports_type
    ON public.analytics_reports(report_type);

ALTER TABLE public.analytics_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own analytics reports" ON public.analytics_reports;
CREATE POLICY "Users can manage their own analytics reports"
    ON public.analytics_reports
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages analytics reports" ON public.analytics_reports;
CREATE POLICY "Service role manages analytics reports"
    ON public.analytics_reports
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_analytics_reports_updated_at ON public.analytics_reports;
CREATE TRIGGER update_analytics_reports_updated_at
    BEFORE UPDATE ON public.analytics_reports
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- journey/activity tracking tables
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.user_activity_log
    ADD COLUMN IF NOT EXISTS details TEXT,
    ADD COLUMN IF NOT EXISTS timestamp TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

UPDATE public.user_activity_log
SET
    timestamp = COALESCE(timestamp, created_at, now()),
    created_at = COALESCE(created_at, now())
WHERE timestamp IS NULL
   OR created_at IS NULL;

ALTER TABLE public.user_activity_log
    ALTER COLUMN timestamp SET DEFAULT now(),
    ALTER COLUMN timestamp SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_timestamp
    ON public.user_activity_log(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_action
    ON public.user_activity_log(action);

ALTER TABLE public.user_activity_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own activity log" ON public.user_activity_log;
CREATE POLICY "Users can manage their own activity log"
    ON public.user_activity_log
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages activity log" ON public.user_activity_log;
CREATE POLICY "Service role manages activity log"
    ON public.user_activity_log
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE TABLE IF NOT EXISTS public.initiative_phase_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id UUID NOT NULL REFERENCES public.initiatives(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    from_phase TEXT,
    to_phase TEXT NOT NULL,
    duration_seconds INTEGER,
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.initiative_phase_history
    ADD COLUMN IF NOT EXISTS from_phase TEXT,
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER,
    ADD COLUMN IF NOT EXISTS transitioned_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

UPDATE public.initiative_phase_history
SET
    transitioned_at = COALESCE(transitioned_at, created_at, now()),
    created_at = COALESCE(created_at, now())
WHERE transitioned_at IS NULL
   OR created_at IS NULL;

ALTER TABLE public.initiative_phase_history
    ALTER COLUMN transitioned_at SET DEFAULT now(),
    ALTER COLUMN transitioned_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_initiative_phase_history_user_transitioned_at
    ON public.initiative_phase_history(user_id, transitioned_at DESC);
CREATE INDEX IF NOT EXISTS idx_initiative_phase_history_initiative
    ON public.initiative_phase_history(initiative_id, transitioned_at DESC);

ALTER TABLE public.initiative_phase_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own initiative phase history" ON public.initiative_phase_history;
CREATE POLICY "Users can manage their own initiative phase history"
    ON public.initiative_phase_history
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages initiative phase history" ON public.initiative_phase_history;
CREATE POLICY "Service role manages initiative phase history"
    ON public.initiative_phase_history
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);
