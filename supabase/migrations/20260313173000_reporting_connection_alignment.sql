-- Migration: 20260313173000_reporting_connection_alignment.sql
-- Description: Canonicalize spreadsheet reporting connections and scheduled report tables.

-- -----------------------------------------------------------------------------
-- spreadsheet_connections
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.spreadsheet_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'google_sheets',
    spreadsheet_id TEXT NOT NULL,
    spreadsheet_name TEXT NOT NULL,
    spreadsheet_url TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.spreadsheet_connections
    ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'google_sheets',
    ADD COLUMN IF NOT EXISTS spreadsheet_name TEXT,
    ADD COLUMN IF NOT EXISTS spreadsheet_url TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.spreadsheet_connections
SET
    provider = COALESCE(provider, 'google_sheets'),
    spreadsheet_name = COALESCE(spreadsheet_name, spreadsheet_id),
    metadata = COALESCE(metadata, '{}'::jsonb),
    is_active = COALESCE(is_active, true),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now())
WHERE provider IS NULL
   OR spreadsheet_name IS NULL
   OR metadata IS NULL
   OR is_active IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE public.spreadsheet_connections
    ALTER COLUMN provider SET DEFAULT 'google_sheets',
    ALTER COLUMN provider SET NOT NULL,
    ALTER COLUMN spreadsheet_name SET NOT NULL,
    ALTER COLUMN metadata SET DEFAULT '{}'::jsonb,
    ALTER COLUMN metadata SET NOT NULL,
    ALTER COLUMN is_active SET DEFAULT true,
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
        WHERE conname = 'spreadsheet_connections_user_provider_sheet_key'
          AND conrelid = 'public.spreadsheet_connections'::regclass
    ) THEN
        ALTER TABLE public.spreadsheet_connections
            ADD CONSTRAINT spreadsheet_connections_user_provider_sheet_key
            UNIQUE (user_id, provider, spreadsheet_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_spreadsheet_connections_user_id
    ON public.spreadsheet_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_spreadsheet_connections_active
    ON public.spreadsheet_connections(user_id, is_active);

ALTER TABLE public.spreadsheet_connections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own spreadsheet connections" ON public.spreadsheet_connections;
CREATE POLICY "Users can view their own spreadsheet connections"
    ON public.spreadsheet_connections
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can insert their own spreadsheet connections" ON public.spreadsheet_connections;
CREATE POLICY "Users can insert their own spreadsheet connections"
    ON public.spreadsheet_connections
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update their own spreadsheet connections" ON public.spreadsheet_connections;
CREATE POLICY "Users can update their own spreadsheet connections"
    ON public.spreadsheet_connections
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete their own spreadsheet connections" ON public.spreadsheet_connections;
CREATE POLICY "Users can delete their own spreadsheet connections"
    ON public.spreadsheet_connections
    FOR DELETE TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Service role manages spreadsheet connections" ON public.spreadsheet_connections;
CREATE POLICY "Service role manages spreadsheet connections"
    ON public.spreadsheet_connections
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_spreadsheet_connections_updated_at ON public.spreadsheet_connections;
CREATE TRIGGER update_spreadsheet_connections_updated_at
    BEFORE UPDATE ON public.spreadsheet_connections
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- report_schedules
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.report_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES public.spreadsheet_connections(id) ON DELETE CASCADE,
    frequency TEXT NOT NULL,
    report_type TEXT NOT NULL DEFAULT 'summary',
    report_format TEXT NOT NULL DEFAULT 'pptx',
    recipients JSONB NOT NULL DEFAULT '[]'::jsonb,
    template_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    next_run_at TIMESTAMPTZ NOT NULL,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.report_schedules
    ADD COLUMN IF NOT EXISTS report_type TEXT DEFAULT 'summary',
    ADD COLUMN IF NOT EXISTS report_format TEXT DEFAULT 'pptx',
    ADD COLUMN IF NOT EXISTS recipients JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS template_config JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.report_schedules
SET
    report_type = COALESCE(report_type, 'summary'),
    report_format = COALESCE(report_format, 'pptx'),
    recipients = COALESCE(recipients, '[]'::jsonb),
    template_config = COALESCE(template_config, '{}'::jsonb),
    enabled = COALESCE(enabled, true),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now()),
    next_run_at = COALESCE(next_run_at, now())
WHERE report_type IS NULL
   OR report_format IS NULL
   OR recipients IS NULL
   OR template_config IS NULL
   OR enabled IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL
   OR next_run_at IS NULL;

ALTER TABLE public.report_schedules
    ALTER COLUMN report_type SET DEFAULT 'summary',
    ALTER COLUMN report_type SET NOT NULL,
    ALTER COLUMN report_format SET DEFAULT 'pptx',
    ALTER COLUMN report_format SET NOT NULL,
    ALTER COLUMN recipients SET DEFAULT '[]'::jsonb,
    ALTER COLUMN recipients SET NOT NULL,
    ALTER COLUMN template_config SET DEFAULT '{}'::jsonb,
    ALTER COLUMN template_config SET NOT NULL,
    ALTER COLUMN enabled SET DEFAULT true,
    ALTER COLUMN enabled SET NOT NULL,
    ALTER COLUMN next_run_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'report_schedules_frequency_check'
          AND conrelid = 'public.report_schedules'::regclass
    ) THEN
        ALTER TABLE public.report_schedules
            ADD CONSTRAINT report_schedules_frequency_check
            CHECK (frequency IN ('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'report_schedules_report_format_check'
          AND conrelid = 'public.report_schedules'::regclass
    ) THEN
        ALTER TABLE public.report_schedules
            ADD CONSTRAINT report_schedules_report_format_check
            CHECK (report_format IN ('pdf', 'pptx', 'xlsx'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_report_schedules_connection_id
    ON public.report_schedules(connection_id);
CREATE INDEX IF NOT EXISTS idx_report_schedules_next_run
    ON public.report_schedules(next_run_at)
    WHERE enabled = true;

ALTER TABLE public.report_schedules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own report schedules" ON public.report_schedules;
CREATE POLICY "Users can view their own report schedules"
    ON public.report_schedules
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.spreadsheet_connections sc
            WHERE sc.id = report_schedules.connection_id
              AND sc.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert their own report schedules" ON public.report_schedules;
CREATE POLICY "Users can insert their own report schedules"
    ON public.report_schedules
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.spreadsheet_connections sc
            WHERE sc.id = report_schedules.connection_id
              AND sc.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can update their own report schedules" ON public.report_schedules;
CREATE POLICY "Users can update their own report schedules"
    ON public.report_schedules
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.spreadsheet_connections sc
            WHERE sc.id = report_schedules.connection_id
              AND sc.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.spreadsheet_connections sc
            WHERE sc.id = report_schedules.connection_id
              AND sc.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can delete their own report schedules" ON public.report_schedules;
CREATE POLICY "Users can delete their own report schedules"
    ON public.report_schedules
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.spreadsheet_connections sc
            WHERE sc.id = report_schedules.connection_id
              AND sc.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Service role manages report schedules" ON public.report_schedules;
CREATE POLICY "Service role manages report schedules"
    ON public.report_schedules
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_report_schedules_updated_at ON public.report_schedules;
CREATE TRIGGER update_report_schedules_updated_at
    BEFORE UPDATE ON public.report_schedules
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- generated_reports
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.generated_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES public.report_schedules(id) ON DELETE SET NULL,
    connection_id UUID REFERENCES public.spreadsheet_connections(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL,
    report_format TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_url TEXT,
    file_size_bytes BIGINT,
    delivery_status TEXT NOT NULL DEFAULT 'pending',
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.generated_reports
    ADD COLUMN IF NOT EXISTS file_url TEXT,
    ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS delivery_status TEXT DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.generated_reports
SET
    delivery_status = COALESCE(delivery_status, 'pending'),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now())
WHERE delivery_status IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE public.generated_reports
    ALTER COLUMN delivery_status SET DEFAULT 'pending',
    ALTER COLUMN delivery_status SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'generated_reports_report_format_check'
          AND conrelid = 'public.generated_reports'::regclass
    ) THEN
        ALTER TABLE public.generated_reports
            ADD CONSTRAINT generated_reports_report_format_check
            CHECK (report_format IN ('pdf', 'pptx', 'xlsx'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'generated_reports_delivery_status_check'
          AND conrelid = 'public.generated_reports'::regclass
    ) THEN
        ALTER TABLE public.generated_reports
            ADD CONSTRAINT generated_reports_delivery_status_check
            CHECK (delivery_status IN ('pending', 'delivered', 'failed'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_generated_reports_connection_id
    ON public.generated_reports(connection_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_schedule_id
    ON public.generated_reports(schedule_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_user_id
    ON public.generated_reports(user_id, created_at DESC);

ALTER TABLE public.generated_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own generated reports" ON public.generated_reports;
CREATE POLICY "Users can view their own generated reports"
    ON public.generated_reports
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can insert their own generated reports" ON public.generated_reports;
CREATE POLICY "Users can insert their own generated reports"
    ON public.generated_reports
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update their own generated reports" ON public.generated_reports;
CREATE POLICY "Users can update their own generated reports"
    ON public.generated_reports
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete their own generated reports" ON public.generated_reports;
CREATE POLICY "Users can delete their own generated reports"
    ON public.generated_reports
    FOR DELETE TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Service role manages generated reports" ON public.generated_reports;
CREATE POLICY "Service role manages generated reports"
    ON public.generated_reports
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_generated_reports_updated_at ON public.generated_reports;
CREATE TRIGGER update_generated_reports_updated_at
    BEFORE UPDATE ON public.generated_reports
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
