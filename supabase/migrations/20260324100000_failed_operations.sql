-- Failed Operations Retry Queue
-- Persists workflow step failures for background retry with exponential backoff.

CREATE TABLE IF NOT EXISTS public.failed_operations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id uuid NOT NULL,
    execution_id uuid NOT NULL,
    tool_name text NOT NULL,
    input_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    step_definition jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message text,
    reason_code text,
    attempt_count integer NOT NULL DEFAULT 0,
    max_retries integer NOT NULL DEFAULT 3,
    next_retry_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'dead_letter')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Index for the retry processor: fetch pending ops due for retry
CREATE INDEX IF NOT EXISTS idx_failed_operations_pending_retry
    ON public.failed_operations (next_retry_at)
    WHERE status = 'pending';

-- Index for lookup by execution
CREATE INDEX IF NOT EXISTS idx_failed_operations_execution
    ON public.failed_operations (execution_id);

-- RLS: service-role only (no user access)
ALTER TABLE public.failed_operations ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "service_role_full_access" ON public.failed_operations
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
